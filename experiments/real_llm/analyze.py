"""Analysis and table generation for real LLM experiment results.

Produces 5 tables + 1 figure for RQ5 paper section:
A: Trace Structure — spans/trace, kind distribution, latency, cost per model
B: Natural Faults — which faults appear organically per model
C: Real FDR — 5 fault types x models, binary detection
D: Cost Accuracy — estimate_cost() vs actual API-reported tokens
E: Overhead — instrumented vs uninstrumented wall-clock time
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from agenttelemetry.analysis import (
    AnomalyDetector,
    CostAggregator,
    DecisionAttributor,
    HallucinationTracer,
)
from agenttelemetry.core.spans import AgentSpanKind

RESULTS_DIR = PROJECT_ROOT / "results" / "real_llm"
TRACES_DIR = RESULTS_DIR / "traces"
TABLES_DIR = RESULTS_DIR / "tables"


def load_traces(pattern: str) -> List[Dict[str, Any]]:
    """Load all spans from trace files matching pattern."""
    spans = []
    for f in sorted(TRACES_DIR.glob(pattern)):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))
    return spans


def load_results(filename: str) -> List[Dict[str, Any]]:
    """Load results JSON."""
    path = RESULTS_DIR / filename
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def table_a_trace_structure():
    """Table A: Trace structure per model."""
    print("\n" + "=" * 80)
    print("TABLE A: Trace Structure by Model")
    print("=" * 80)

    results = load_results("phase1_results.json")
    if not results:
        print("  No phase 1 results found.")
        return

    # Group by model
    by_model: Dict[str, List[Dict]] = defaultdict(list)
    for r in results:
        if r.get("error") and r["error"] != "max_iterations_reached":
            continue
        by_model[r["model"]].append(r)

    header = f"{'Model':<20} {'Runs':>5} {'Avg Iter':>8} {'Avg Tools':>9} {'Avg In Tok':>10} {'Avg Out Tok':>11} {'Errors':>6}"
    print(header)
    print("-" * len(header))

    table_data = []
    for model, runs in sorted(by_model.items()):
        n = len(runs)
        avg_iter = sum(r.get("iterations", 0) for r in runs) / max(n, 1)
        avg_tools = sum(len(r.get("tool_calls_made", [])) for r in runs) / max(n, 1)
        avg_in = sum(r.get("total_input_tokens", 0) for r in runs) / max(n, 1)
        avg_out = sum(r.get("total_output_tokens", 0) for r in runs) / max(n, 1)
        errors = sum(1 for r in runs if r.get("error"))

        print(f"{model:<20} {n:>5} {avg_iter:>8.1f} {avg_tools:>9.1f} {avg_in:>10.0f} {avg_out:>11.0f} {errors:>6}")
        table_data.append({
            "model": model,
            "runs": n,
            "avg_iterations": round(avg_iter, 1),
            "avg_tools": round(avg_tools, 1),
            "avg_input_tokens": round(avg_in),
            "avg_output_tokens": round(avg_out),
            "errors": errors,
        })

    # Span kind distribution from traces
    spans = load_traces("phase1_*.jsonl")
    if spans:
        print(f"\nSpan Kind Distribution ({len(spans)} total spans):")
        kind_counts: Dict[str, int] = defaultdict(int)
        for s in spans:
            kind = s.get("agent_span_kind", "UNKNOWN")
            kind_counts[kind] += 1
        for kind, count in sorted(kind_counts.items(), key=lambda x: -x[1]):
            pct = count / len(spans) * 100
            print(f"  {kind:<15} {count:>6} ({pct:>5.1f}%)")

    # Save
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TABLES_DIR / "table_a_trace_structure.json", "w") as f:
        json.dump(table_data, f, indent=2)


def table_b_natural_faults():
    """Table B: Natural faults found in clean traces."""
    print("\n" + "=" * 80)
    print("TABLE B: Natural Faults in Clean Traces")
    print("=" * 80)

    detector = AnomalyDetector(
        max_retries=3,
        cost_threshold=0.05,
        token_growth_factor=1.5,
    )
    hallucination_tracer = HallucinationTracer(min_confidence=0.3)

    table_data = []
    for trace_file in sorted(TRACES_DIR.glob("phase1_*.jsonl")):
        model = trace_file.stem.replace("phase1_", "")
        spans = []
        with open(trace_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))

        if not spans:
            continue

        anomalies = detector.detect(spans)
        hallucinations = hallucination_tracer.analyze(spans)

        if anomalies or hallucinations:
            print(f"\n  {model}:")
            for a in anomalies:
                print(f"    [{a.severity}] {a.anomaly_type.value}: {a.description[:80]}")
            for h in hallucinations:
                print(f"    [hallucination {h.confidence:.2f}] {h.claim[:60]}...")

        table_data.append({
            "model": model,
            "anomaly_count": len(anomalies),
            "anomalies": [
                {"type": a.anomaly_type.value, "severity": a.severity}
                for a in anomalies
            ],
            "hallucination_count": len(hallucinations),
        })

    if not any(d["anomaly_count"] > 0 or d["hallucination_count"] > 0 for d in table_data):
        print("  No natural faults detected in any model's clean traces.")

    with open(TABLES_DIR / "table_b_natural_faults.json", "w") as f:
        json.dump(table_data, f, indent=2)


def table_c_real_fdr():
    """Table C: Fault detection rate per fault type x model."""
    print("\n" + "=" * 80)
    print("TABLE C: Real Fault Detection Rate (FDR)")
    print("=" * 80)

    detector = AnomalyDetector(
        max_retries=3,
        cost_threshold=0.05,
        token_growth_factor=1.5,
    )
    attributor = DecisionAttributor()

    results = load_results("phase3_results.json")
    if not results:
        print("  No phase 3 results found.")
        return

    # For each fault x model, check if detector finds it
    from experiments.real_llm.fault_conditions import FAULT_CONDITIONS

    fault_names = [f.name for f in FAULT_CONDITIONS]
    models_seen = set()
    detection_matrix: Dict[str, Dict[str, bool]] = defaultdict(dict)

    # Known fault names for parsing filenames
    _FAULT_NAMES = {"context_overflow", "tool_failure", "wrong_tool", "cost_explosion", "missing_guardrail"}

    for trace_file in sorted(TRACES_DIR.glob("phase3_*.jsonl")):
        stem = trace_file.stem.replace("phase3_", "")
        # Parse model and fault from filename like "gpt-4o-mini_context_overflow"
        model = None
        fault = None
        for fn in _FAULT_NAMES:
            if stem.endswith("_" + fn):
                model = stem[:-(len(fn) + 1)]
                fault = fn
                break
        if not model or not fault:
            continue
        models_seen.add(model)

        spans = []
        with open(trace_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))

        if not spans:
            detection_matrix[fault][model] = False
            continue

        detected = False

        # Check anomaly detector
        anomalies = detector.detect(spans)
        if anomalies:
            detected = True

        # For wrong_tool: check decision attributor
        if fault == "wrong_tool":
            decisions = attributor.analyze(spans)
            # Check if tools used don't match expected
            for d in decisions:
                if d.tool_name in ("search_kb",) and d.reasoning:
                    if "calculator" in d.reasoning.lower() or "math" in d.reasoning.lower():
                        detected = True

        # For missing_guardrail: check for absent GUARD_RAIL spans
        if fault == "missing_guardrail":
            has_guardrail = any(
                s.get("agent_span_kind") == AgentSpanKind.GUARD_RAIL
                for s in spans
            )
            if not has_guardrail:
                detected = True

        detection_matrix[fault][model] = detected

    # Print matrix
    models = sorted(models_seen)
    header = f"{'Fault':<20}" + "".join(f" {m[:12]:>12}" for m in models) + "  FDR"
    print(header)
    print("-" * len(header))

    table_data = []
    for fault in fault_names:
        detections = detection_matrix.get(fault, {})
        row = f"{fault:<20}"
        detected_count = 0
        total_count = 0
        for m in models:
            if m in detections:
                total_count += 1
                if detections[m]:
                    detected_count += 1
                    row += f" {'✓':>12}"
                else:
                    row += f" {'✗':>12}"
            else:
                row += f" {'-':>12}"
        fdr = detected_count / total_count if total_count > 0 else 0
        row += f"  {fdr:.2f}"
        print(row)

        table_data.append({
            "fault": fault,
            "detections": dict(detections),
            "fdr": fdr,
        })

    with open(TABLES_DIR / "table_c_real_fdr.json", "w") as f:
        json.dump(table_data, f, indent=2)


def table_d_cost_accuracy():
    """Table D: Cost estimation accuracy."""
    print("\n" + "=" * 80)
    print("TABLE D: Cost Estimation Accuracy")
    print("=" * 80)

    aggregator = CostAggregator()

    table_data = []
    for trace_file in sorted(TRACES_DIR.glob("phase1_*.jsonl")):
        model = trace_file.stem.replace("phase1_", "")
        spans = []
        with open(trace_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))

        if not spans:
            continue

        report = aggregator.analyze(spans)
        if report.total_cost > 0:
            table_data.append({
                "model": model,
                "total_cost": round(report.total_cost, 6),
                "total_input_tokens": report.total_input_tokens,
                "total_output_tokens": report.total_output_tokens,
                "calls": sum(mc.call_count for mc in report.by_model.values()),
            })

    if table_data:
        header = f"{'Model':<20} {'Cost ($)':>10} {'In Tokens':>10} {'Out Tokens':>10} {'Calls':>6}"
        print(header)
        print("-" * len(header))
        for d in table_data:
            print(f"{d['model']:<20} {d['total_cost']:>10.6f} {d['total_input_tokens']:>10} {d['total_output_tokens']:>10} {d['calls']:>6}")

        total_cost = sum(d["total_cost"] for d in table_data)
        print(f"\n  Total estimated cost: ${total_cost:.4f}")
    else:
        print("  No cost data available.")

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TABLES_DIR / "table_d_cost_accuracy.json", "w") as f:
        json.dump(table_data, f, indent=2)


def table_e_overhead():
    """Table E: Instrumentation overhead."""
    print("\n" + "=" * 80)
    print("TABLE E: Instrumentation Overhead")
    print("=" * 80)

    results = load_results("phase4_results.json")
    if not results:
        print("  No phase 4 results found.")
        return

    header = f"{'Model':<20} {'Q':>3} {'Instrumented (s)':>16} {'Raw (s)':>10} {'Overhead %':>10}"
    print(header)
    print("-" * len(header))

    table_data = []
    for r in results:
        overhead = r.get("overhead_pct", 0)
        print(
            f"{r['model']:<20} {r['question_id']:>3} "
            f"{r['time_instrumented_s']:>16.3f} "
            f"{r['time_uninstrumented_s']:>10.3f} "
            f"{overhead:>10.1f}%"
        )
        table_data.append(r)

    if results:
        avg_overhead = sum(r.get("overhead_pct", 0) for r in results) / len(results)
        print(f"\n  Average overhead: {avg_overhead:.1f}%")

    with open(TABLES_DIR / "table_e_overhead.json", "w") as f:
        json.dump(table_data, f, indent=2)


def generate_trace_tree():
    """Generate a representative trace tree visualization."""
    print("\n" + "=" * 80)
    print("TRACE TREE: Representative Trace")
    print("=" * 80)

    # Find a representative trace from phase 1
    for trace_file in sorted(TRACES_DIR.glob("phase1_gpt-4o-mini.jsonl")):
        spans = []
        with open(trace_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))

        if not spans:
            continue

        # Group by trace
        traces: Dict[str, List[Dict]] = defaultdict(list)
        for s in spans:
            traces[s.get("trace_id", "")].append(s)

        # Pick the first complete trace
        for trace_id, trace_spans in traces.items():
            if len(trace_spans) >= 5:  # Minimum meaningful trace
                _render_trace_tree(trace_spans, trace_id)
                return

    # Fallback: try any phase1 file
    for trace_file in sorted(TRACES_DIR.glob("phase1_*.jsonl")):
        spans = []
        with open(trace_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))
        if spans:
            traces: Dict[str, List[Dict]] = defaultdict(list)
            for s in spans:
                traces[s.get("trace_id", "")].append(s)
            for trace_id, trace_spans in traces.items():
                if len(trace_spans) >= 5:
                    _render_trace_tree(trace_spans, trace_id)
                    return

    print("  No suitable trace found for visualization.")


def _render_trace_tree(spans: List[Dict], trace_id: str):
    """Render a span tree to console and save as text."""
    # Build tree
    by_id = {s["span_id"]: s for s in spans}
    children: Dict[str, List[str]] = defaultdict(list)
    roots = []

    for s in spans:
        parent = s.get("parent_span_id")
        if parent and parent in by_id:
            children[parent].append(s["span_id"])
        else:
            roots.append(s["span_id"])

    # Sort by start time
    def sort_key(sid):
        return by_id[sid].get("start_time_ns", 0) or 0

    lines = []

    def render(sid, depth=0):
        s = by_id[sid]
        kind = s.get("agent_span_kind", "?")
        name = s.get("name", "?")
        dur = s.get("duration_ms", 0)
        prefix = "  " * depth + ("├─ " if depth > 0 else "")
        line = f"{prefix}[{kind}] {name} ({dur:.0f}ms)"
        lines.append(line)
        print(line)

        for child_id in sorted(children.get(sid, []), key=sort_key):
            render(child_id, depth + 1)

    print(f"\nTrace: {trace_id[:16]}...")
    lines.append(f"Trace: {trace_id[:16]}...")

    for root in sorted(roots, key=sort_key):
        render(root)

    # Save
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TABLES_DIR / "trace_tree.txt", "w") as f:
        f.write("\n".join(lines))


def main():
    """Generate all tables and visualizations."""
    print("=" * 80)
    print("AgentTelemetry Real LLM Experiment — Analysis")
    print("=" * 80)

    table_a_trace_structure()
    table_b_natural_faults()
    table_c_real_fdr()
    table_d_cost_accuracy()
    table_e_overhead()
    generate_trace_tree()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print(f"Tables saved to: {TABLES_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()
