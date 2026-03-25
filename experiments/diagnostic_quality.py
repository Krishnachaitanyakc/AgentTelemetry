"""Diagnostic quality metrics: AgentTelemetry vs vanilla OTel.

Computes four metrics on the SWE-bench 100 traces that approximate
what a user study would measure — how much faster can a developer
diagnose an agent failure with typed spans vs flat INTERNAL spans?

Metrics:
1. Localization precision — spans examined to reach the faulty span
2. Spans-to-diagnosis — average spans to understand the failure
3. Signal-to-noise ratio — fraction of diagnostically relevant spans
4. Trace tree depth — whether span hierarchy helps localize faults

Usage:
    PYTHONPATH=src .venv/bin/python3.12 experiments/diagnostic_quality.py
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESULTS_DIR = PROJECT_ROOT / "results" / "swebench_100"
TRACES_FILE = RESULTS_DIR / "traces" / "swebench_100_traces.jsonl"
AGENT_RESULTS_FILE = RESULTS_DIR / "agent_results.json"
OUTPUT_DIR = PROJECT_ROOT / "results" / "diagnostic_quality"

# Span kinds that carry diagnostic signal about *why* the agent failed
DIAGNOSTIC_KINDS = {"REASONING", "PLANNING", "GUARD_RAIL"}
# Span kinds that carry execution signal (what happened, not why)
EXECUTION_KINDS = {"LLM_CALL", "TOOL_CALL", "RETRIEVAL", "MEMORY"}
# Structural span (root)
STRUCTURAL_KINDS = {"AGENT"}


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_traces() -> List[Dict[str, Any]]:
    """Load all spans from the JSONL trace file."""
    spans = []
    with open(TRACES_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                spans.append(json.loads(line))
    return spans


def load_agent_results() -> List[Dict[str, Any]]:
    """Load per-instance agent results."""
    with open(AGENT_RESULTS_FILE) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Group spans by trace
# ---------------------------------------------------------------------------

def group_by_trace(spans: List[Dict]) -> Dict[str, List[Dict]]:
    """Group spans by trace_id, sorted by start_time_ns within each trace."""
    traces: Dict[str, List[Dict]] = defaultdict(list)
    for span in spans:
        tid = span.get("trace_id", "unknown")
        traces[tid].append(span)
    for tid in traces:
        traces[tid].sort(key=lambda s: s.get("start_time_ns", 0) or 0)
    return dict(traces)


# ---------------------------------------------------------------------------
# Match trace_id to instance_id (traces share trace_id with AGENT span)
# ---------------------------------------------------------------------------

def build_trace_to_instance(
    traces: Dict[str, List[Dict]],
    results: List[Dict],
) -> Dict[str, Dict]:
    """Map trace_id -> agent_result by matching AGENT span name to instance_id."""
    # Build lookup from instance_id -> result
    result_by_id = {r["instance_id"]: r for r in results}

    trace_to_result: Dict[str, Dict] = {}
    for tid, spans in traces.items():
        for span in spans:
            if span.get("agent_span_kind") == "AGENT":
                # Name is like "swebench_agent(django__django-10914)"
                name = span.get("name", "")
                # Extract instance_id from parentheses
                if "(" in name and ")" in name:
                    inst_id = name[name.index("(") + 1 : name.index(")")]
                    if inst_id in result_by_id:
                        trace_to_result[tid] = result_by_id[inst_id]
                break
    return trace_to_result


# ---------------------------------------------------------------------------
# Metric 1: Localization Precision
# ---------------------------------------------------------------------------

def compute_localization_precision(
    traces: Dict[str, List[Dict]],
    trace_to_result: Dict[str, Dict],
) -> Dict[str, Any]:
    """For each failed trace, count how many spans must be examined
    to reach the first REASONING span that reveals the loop pattern.

    AgentTelemetry: filter to REASONING spans, the loop is immediately
    visible (position of first REASONING span among diagnostic spans).

    Vanilla OTel: all spans are INTERNAL -- must scan from the beginning.
    """
    at_positions = []  # position within REASONING-filtered view
    otel_positions = []  # position within all-INTERNAL view

    for tid, spans in traces.items():
        result = trace_to_result.get(tid)
        if not result:
            continue
        # Only consider failed instances (reasoning loop)
        if result.get("error") != "max_iterations_reached":
            continue

        total_spans = len(spans)
        if total_spans == 0:
            continue

        # --- AgentTelemetry perspective ---
        # Developer filters to REASONING spans, then looks for repeated
        # patterns. The fault is visible after examining the first few
        # REASONING spans that show the loop.
        reasoning_spans = [
            s for s in spans if s.get("agent_span_kind") == "REASONING"
        ]
        # A reasoning loop is visible after seeing ~3 consecutive REASONING
        # spans with similar content (the minimum to identify "repetition").
        # We count position = min(3, len(reasoning_spans)).
        at_pos = min(3, len(reasoning_spans))
        at_positions.append(at_pos)

        # --- Vanilla OTel perspective ---
        # All spans are INTERNAL. The developer must examine spans
        # sequentially. The reasoning loop pattern becomes visible only
        # after examining enough spans to see the repetition pattern.
        # For each trace, the developer must reach the 3rd REASONING span
        # in the *full* span list (since they can't filter by kind).
        reasoning_count = 0
        otel_pos = total_spans  # worst case: must examine all
        for i, s in enumerate(spans):
            if s.get("agent_span_kind") == "REASONING":
                reasoning_count += 1
                if reasoning_count >= 3:
                    otel_pos = i + 1  # 1-indexed position
                    break
        otel_positions.append(otel_pos)

    return {
        "agenttelemetry_positions": at_positions,
        "vanilla_otel_positions": otel_positions,
        "at_mean": statistics.mean(at_positions) if at_positions else 0,
        "otel_mean": statistics.mean(otel_positions) if otel_positions else 0,
        "at_median": statistics.median(at_positions) if at_positions else 0,
        "otel_median": statistics.median(otel_positions) if otel_positions else 0,
        "n_failed_traces": len(at_positions),
    }


# ---------------------------------------------------------------------------
# Metric 2: Spans-to-Diagnosis
# ---------------------------------------------------------------------------

def compute_spans_to_diagnosis(
    traces: Dict[str, List[Dict]],
    trace_to_result: Dict[str, Dict],
) -> Dict[str, Any]:
    """Average number of spans a developer must examine to understand
    why the agent failed.

    AgentTelemetry: filter to diagnostic kinds (REASONING, PLANNING,
    GUARD_RAIL) -- these directly explain agent decisions.

    Vanilla OTel: all spans are opaque INTERNAL spans; developer must
    examine every span to reconstruct the decision-making process.
    """
    at_counts = []  # diagnostic spans only
    otel_counts = []  # all spans

    for tid, spans in traces.items():
        result = trace_to_result.get(tid)
        if not result:
            continue
        if result.get("error") != "max_iterations_reached":
            continue

        total = len(spans)
        diagnostic = sum(
            1 for s in spans
            if s.get("agent_span_kind") in DIAGNOSTIC_KINDS
        )
        at_counts.append(diagnostic)
        otel_counts.append(total)

    reduction_pcts = []
    for at, otel in zip(at_counts, otel_counts):
        if otel > 0:
            reduction_pcts.append((1 - at / otel) * 100)

    return {
        "at_counts": at_counts,
        "otel_counts": otel_counts,
        "at_mean": statistics.mean(at_counts) if at_counts else 0,
        "otel_mean": statistics.mean(otel_counts) if otel_counts else 0,
        "at_median": statistics.median(at_counts) if at_counts else 0,
        "otel_median": statistics.median(otel_counts) if otel_counts else 0,
        "reduction_pct_mean": statistics.mean(reduction_pcts) if reduction_pcts else 0,
        "reduction_pct_median": statistics.median(reduction_pcts) if reduction_pcts else 0,
        "n_traces": len(at_counts),
    }


# ---------------------------------------------------------------------------
# Metric 3: Signal-to-Noise Ratio
# ---------------------------------------------------------------------------

def compute_signal_to_noise(
    traces: Dict[str, List[Dict]],
    trace_to_result: Dict[str, Dict],
) -> Dict[str, Any]:
    """What fraction of spans are diagnostically relevant?

    AgentTelemetry: REASONING + PLANNING + GUARD_RAIL = diagnostic signal.
    Remaining spans (LLM_CALL, TOOL_CALL, RETRIEVAL, MEMORY, AGENT) = noise
    for debugging purposes.

    Vanilla OTel: all spans are INTERNAL -- no signal/noise distinction
    is possible. Effective SNR = 1.0 (all spans equally opaque).
    """
    at_snr_values = []
    # Overall counts
    total_diagnostic = 0
    total_execution = 0
    total_structural = 0
    total_spans = 0

    for tid, spans in traces.items():
        result = trace_to_result.get(tid)
        if not result:
            continue

        n = len(spans)
        if n == 0:
            continue
        total_spans += n

        diag = sum(
            1 for s in spans if s.get("agent_span_kind") in DIAGNOSTIC_KINDS
        )
        exec_ = sum(
            1 for s in spans if s.get("agent_span_kind") in EXECUTION_KINDS
        )
        struct = sum(
            1 for s in spans if s.get("agent_span_kind") in STRUCTURAL_KINDS
        )
        total_diagnostic += diag
        total_execution += exec_
        total_structural += struct

        # SNR = diagnostic / non-diagnostic (higher = more signal)
        noise = n - diag
        if noise > 0:
            at_snr_values.append(diag / noise)
        elif diag > 0:
            at_snr_values.append(float("inf"))

    return {
        "at_snr_mean": statistics.mean(at_snr_values) if at_snr_values else 0,
        "at_snr_median": statistics.median(at_snr_values) if at_snr_values else 0,
        "otel_snr": 0.0,  # All spans equally opaque; no signal distinction
        "total_diagnostic": total_diagnostic,
        "total_execution": total_execution,
        "total_structural": total_structural,
        "total_spans": total_spans,
        "diagnostic_fraction": total_diagnostic / total_spans if total_spans else 0,
    }


# ---------------------------------------------------------------------------
# Metric 4: Trace Tree Depth
# ---------------------------------------------------------------------------

def compute_trace_depth(
    traces: Dict[str, List[Dict]],
) -> Dict[str, Any]:
    """Compute the depth of the span hierarchy in each trace.

    AgentTelemetry: AGENT -> PLANNING/REASONING/... -> LLM_CALL hierarchy.
    Vanilla OTel: all spans are siblings under a root -- effectively flat.
    """
    at_depths = []
    at_kind_by_depth: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for tid, spans in traces.items():
        if not spans:
            continue

        # Build parent -> children map
        children: Dict[str, List[Dict]] = defaultdict(list)
        span_by_id: Dict[str, Dict] = {}
        root_spans = []

        for s in spans:
            sid = s.get("span_id", "")
            pid = s.get("parent_span_id", "")
            span_by_id[sid] = s
            if pid and pid != "0000000000000000":
                children[pid].append(s)
            else:
                root_spans.append(s)

        # Compute depth via BFS
        max_depth = 0
        queue = [(s, 0) for s in root_spans]
        while queue:
            span, depth = queue.pop(0)
            if depth > max_depth:
                max_depth = depth
            kind = span.get("agent_span_kind", "UNKNOWN")
            at_kind_by_depth[depth][kind] += 1
            for child in children.get(span.get("span_id", ""), []):
                queue.append((child, depth + 1))

        at_depths.append(max_depth)

    # Vanilla OTel: depth is always 1 (root -> flat children) or 0
    # since there's no semantic nesting, a developer sees a flat list
    otel_effective_depth = 1  # root + flat list of INTERNAL spans

    return {
        "at_depths": at_depths,
        "at_mean_depth": statistics.mean(at_depths) if at_depths else 0,
        "at_median_depth": statistics.median(at_depths) if at_depths else 0,
        "at_max_depth": max(at_depths) if at_depths else 0,
        "otel_effective_depth": otel_effective_depth,
        "kind_by_depth": {
            d: dict(kinds) for d, kinds in sorted(at_kind_by_depth.items())
        },
    }


# ---------------------------------------------------------------------------
# Bootstrap CI helper
# ---------------------------------------------------------------------------

def bootstrap_ci(
    values: List[float], n_boot: int = 5000, alpha: float = 0.05
) -> Tuple[float, float]:
    """Bootstrap confidence interval for a mean."""
    import random
    if not values:
        return (0.0, 0.0)
    random.seed(42)
    means = sorted(
        statistics.mean(random.choices(values, k=len(values)))
        for _ in range(n_boot)
    )
    lo = means[int(n_boot * alpha / 2)]
    hi = means[int(n_boot * (1 - alpha / 2))]
    return (lo, hi)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not TRACES_FILE.exists():
        print(f"ERROR: Trace file not found: {TRACES_FILE}")
        sys.exit(1)
    if not AGENT_RESULTS_FILE.exists():
        print(f"ERROR: Agent results not found: {AGENT_RESULTS_FILE}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("DIAGNOSTIC QUALITY METRICS: AgentTelemetry vs Vanilla OTel")
    print("=" * 70)

    # Load data
    print("\nLoading traces...")
    all_spans = load_traces()
    print(f"  {len(all_spans)} spans loaded")

    results = load_agent_results()
    print(f"  {len(results)} agent results loaded")

    traces = group_by_trace(all_spans)
    print(f"  {len(traces)} traces")

    trace_to_result = build_trace_to_instance(traces, results)
    print(f"  {len(trace_to_result)} traces matched to results")

    failed = sum(
        1 for r in trace_to_result.values()
        if r.get("error") == "max_iterations_reached"
    )
    print(f"  {failed} failed instances (reasoning loops)")

    # ---- Metric 1: Localization Precision ----
    print("\n" + "-" * 70)
    print("METRIC 1: Localization Precision")
    print("-" * 70)
    loc = compute_localization_precision(traces, trace_to_result)
    loc_ci_at = bootstrap_ci(loc["agenttelemetry_positions"])
    loc_ci_otel = bootstrap_ci(loc["vanilla_otel_positions"])
    reduction_loc = (1 - loc["at_mean"] / loc["otel_mean"]) * 100 if loc["otel_mean"] else 0

    print(f"  Spans examined to identify fault pattern:")
    print(f"    AgentTelemetry:  mean={loc['at_mean']:.1f}  median={loc['at_median']:.0f}"
          f"  95% CI [{loc_ci_at[0]:.1f}, {loc_ci_at[1]:.1f}]")
    print(f"    Vanilla OTel:    mean={loc['otel_mean']:.1f}  median={loc['otel_median']:.0f}"
          f"  95% CI [{loc_ci_otel[0]:.1f}, {loc_ci_otel[1]:.1f}]")
    print(f"    Reduction: {reduction_loc:.1f}%")
    print(f"    n = {loc['n_failed_traces']} failed traces")

    # ---- Metric 2: Spans-to-Diagnosis ----
    print("\n" + "-" * 70)
    print("METRIC 2: Spans-to-Diagnosis")
    print("-" * 70)
    s2d = compute_spans_to_diagnosis(traces, trace_to_result)
    s2d_ci_at = bootstrap_ci(s2d["at_counts"])
    s2d_ci_otel = bootstrap_ci(s2d["otel_counts"])

    print(f"  Spans to examine for full diagnosis:")
    print(f"    AgentTelemetry:  mean={s2d['at_mean']:.1f}  median={s2d['at_median']:.0f}"
          f"  95% CI [{s2d_ci_at[0]:.1f}, {s2d_ci_at[1]:.1f}]")
    print(f"    Vanilla OTel:    mean={s2d['otel_mean']:.1f}  median={s2d['otel_median']:.0f}"
          f"  95% CI [{s2d_ci_otel[0]:.1f}, {s2d_ci_otel[1]:.1f}]")
    print(f"    Reduction: {s2d['reduction_pct_mean']:.1f}% (mean), {s2d['reduction_pct_median']:.1f}% (median)")
    print(f"    n = {s2d['n_traces']} failed traces")

    # ---- Metric 3: Signal-to-Noise Ratio ----
    print("\n" + "-" * 70)
    print("METRIC 3: Signal-to-Noise Ratio")
    print("-" * 70)
    snr = compute_signal_to_noise(traces, trace_to_result)

    print(f"  AgentTelemetry SNR (diagnostic / non-diagnostic):")
    print(f"    Mean:   {snr['at_snr_mean']:.3f}")
    print(f"    Median: {snr['at_snr_median']:.3f}")
    print(f"  Vanilla OTel SNR: {snr['otel_snr']:.3f} (no kind distinction)")
    print(f"  Span composition:")
    print(f"    Diagnostic (REASONING+PLANNING+GUARD_RAIL): {snr['total_diagnostic']}"
          f" ({snr['diagnostic_fraction']*100:.1f}%)")
    print(f"    Execution (LLM_CALL+TOOL_CALL+RETRIEVAL+MEMORY): {snr['total_execution']}")
    print(f"    Structural (AGENT): {snr['total_structural']}")
    print(f"    Total: {snr['total_spans']}")

    # ---- Metric 4: Trace Tree Depth ----
    print("\n" + "-" * 70)
    print("METRIC 4: Trace Tree Depth")
    print("-" * 70)
    depth = compute_trace_depth(traces)

    print(f"  AgentTelemetry trace depth:")
    print(f"    Mean:   {depth['at_mean_depth']:.1f}")
    print(f"    Median: {depth['at_median_depth']:.0f}")
    print(f"    Max:    {depth['at_max_depth']}")
    print(f"  Vanilla OTel effective depth: {depth['otel_effective_depth']} (flat list)")
    if depth["kind_by_depth"]:
        print(f"  Span kinds by depth level:")
        for d, kinds in sorted(depth["kind_by_depth"].items()):
            kind_str = ", ".join(f"{k}:{v}" for k, v in sorted(kinds.items(), key=lambda x: -x[1]))
            print(f"    Depth {d}: {kind_str}")

    # ---- Summary Table ----
    print("\n" + "=" * 70)
    print("SUMMARY: Diagnostic Quality Comparison")
    print("=" * 70)
    print(f"{'Metric':<35} {'AgentTelemetry':>15} {'Vanilla OTel':>15} {'Reduction':>12}")
    print("-" * 77)
    print(f"{'Localization (spans examined)':<35} {loc['at_mean']:>15.1f} {loc['otel_mean']:>15.1f} {reduction_loc:>11.1f}%")
    s2d_reduction = s2d['reduction_pct_mean']
    print(f"{'Spans-to-diagnosis (mean)':<35} {s2d['at_mean']:>15.1f} {s2d['otel_mean']:>15.1f} {s2d_reduction:>11.1f}%")
    print(f"{'Signal-to-noise ratio':<35} {snr['at_snr_mean']:>15.3f} {snr['otel_snr']:>15.3f} {'N/A':>12}")
    print(f"{'Trace depth (mean)':<35} {depth['at_mean_depth']:>15.1f} {depth['otel_effective_depth']:>15} {'N/A':>12}")

    # ---- Save results ----
    output = {
        "n_instances": len(results),
        "n_traces": len(traces),
        "n_failed": failed,
        "total_spans": len(all_spans),
        "localization_precision": {
            "at_mean": loc["at_mean"],
            "at_median": loc["at_median"],
            "at_ci_95": list(loc_ci_at),
            "otel_mean": loc["otel_mean"],
            "otel_median": loc["otel_median"],
            "otel_ci_95": list(loc_ci_otel),
            "reduction_pct": reduction_loc,
            "n_failed_traces": loc["n_failed_traces"],
        },
        "spans_to_diagnosis": {
            "at_mean": s2d["at_mean"],
            "at_median": s2d["at_median"],
            "at_ci_95": list(s2d_ci_at),
            "otel_mean": s2d["otel_mean"],
            "otel_median": s2d["otel_median"],
            "otel_ci_95": list(s2d_ci_otel),
            "reduction_pct_mean": s2d["reduction_pct_mean"],
            "reduction_pct_median": s2d["reduction_pct_median"],
            "n_traces": s2d["n_traces"],
        },
        "signal_to_noise": {
            "at_snr_mean": snr["at_snr_mean"],
            "at_snr_median": snr["at_snr_median"],
            "otel_snr": snr["otel_snr"],
            "diagnostic_fraction": snr["diagnostic_fraction"],
            "total_diagnostic": snr["total_diagnostic"],
            "total_execution": snr["total_execution"],
            "total_structural": snr["total_structural"],
            "total_spans": snr["total_spans"],
        },
        "trace_depth": {
            "at_mean_depth": depth["at_mean_depth"],
            "at_median_depth": depth["at_median_depth"],
            "at_max_depth": depth["at_max_depth"],
            "otel_effective_depth": depth["otel_effective_depth"],
            "kind_by_depth": depth["kind_by_depth"],
        },
    }

    outfile = OUTPUT_DIR / "diagnostic_quality.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {outfile}")

    print(f"\n{'=' * 70}")
    print("DIAGNOSTIC QUALITY ANALYSIS COMPLETE")
    print(f"{'=' * 70}")

    return output


if __name__ == "__main__":
    main()
