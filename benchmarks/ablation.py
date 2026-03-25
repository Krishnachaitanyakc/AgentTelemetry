"""Span kind ablation study for AgentTelemetry.

Removes each of the 9 span kinds one at a time from detection, measures
FDR degradation. Builds a necessity matrix showing which span kinds are
required for which fault types.

Addresses reviewer concern C3: "9 span kinds introduced without justification."

Usage:
    cd agenttelemetry
    PYTHONPATH=src:. python benchmarks/ablation.py
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SCRIPT_DIR)
_SRC_DIR = os.path.join(_ROOT_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from agenttelemetry.core.spans import AgentSpanKind, AGENT_SPAN_KIND

from benchmarks.run_benchmarks import (
    run_single_benchmark,
    MODELS,
    BenchmarkResult,
)
from benchmarks.faults import FaultType


# All 9 span kinds
ALL_SPAN_KINDS = [
    AgentSpanKind.AGENT,
    AgentSpanKind.LLM_CALL,
    AgentSpanKind.TOOL_CALL,
    AgentSpanKind.PLANNING,
    AgentSpanKind.REASONING,
    AgentSpanKind.RETRIEVAL,
    AgentSpanKind.GUARD_RAIL,
    AgentSpanKind.DELEGATION,
    AgentSpanKind.MEMORY,
]

ALL_FAULT_TYPES = list(FaultType)


@dataclass
class AblationResult:
    """Result of removing one span kind."""
    removed_kind: str
    fault_type: str
    fdr_with: float      # FDR with span kind present (baseline)
    fdr_without: float   # FDR with span kind removed
    fdr_delta: float     # fdr_with - fdr_without
    necessity: str       # "required", "helpful", "unused"


def _strip_span_kind(spans: List[Dict[str, Any]], kind_to_remove: str) -> List[Dict[str, Any]]:
    """Remove all spans of a given agent span kind from a trace.

    Returns a new list with matching spans removed entirely.
    This simulates not having that span kind in the taxonomy.
    """
    return [
        s for s in spans
        if s.get("attributes", {}).get(AGENT_SPAN_KIND) != kind_to_remove
        and s.get("agent_span_kind") != kind_to_remove
    ]


def run_ablation(
    models: Optional[List[str]] = None,
    output_file: str = "benchmarks/ablation_results.tsv",
    verbose: bool = True,
) -> List[AblationResult]:
    """Run the full ablation study.

    For each span kind, removes it from detection and measures FDR impact
    across all fault types.

    Args:
        models: Models to test. Defaults to first 2 for speed.
        output_file: Path for TSV output.
        verbose: Print progress.

    Returns:
        List of AblationResult.
    """
    models = models or MODELS[:2]  # Use 2 models for speed
    framework = "custom"
    condition = "full_capture"

    # Step 1: Baseline FDR (all span kinds present)
    if verbose:
        print("=" * 70)
        print("ABLATION STUDY: Span Kind Necessity Analysis")
        print("=" * 70)
        print(f"\nBaseline run (all 9 span kinds present)...")

    baseline_fdr: Dict[str, float] = {}
    for ft in ALL_FAULT_TYPES:
        fdrs = []
        for model in models:
            result = run_single_benchmark(framework, model, ft, condition)
            fdrs.append(result.fault_detection_rate)
        baseline_fdr[ft.value] = sum(fdrs) / len(fdrs)
        if verbose:
            print(f"  {ft.value:>22}: FDR={baseline_fdr[ft.value]:.3f}")

    # Step 2: For each span kind, run with that kind removed
    ablation_results: List[AblationResult] = []

    for kind in ALL_SPAN_KINDS:
        if verbose:
            print(f"\nAblation: removing {kind}...")

        for ft in ALL_FAULT_TYPES:
            fdrs = []
            for model in models:
                # Run the benchmark
                result = run_single_benchmark(framework, model, ft, condition)

                # Now check: would detection still work without this span kind?
                # Re-run analysis with spans of this kind stripped
                from benchmarks.run_benchmarks import _analyze_traces
                from benchmarks.faults import FaultInjector

                # Recreate the trace and strip the span kind
                injector = FaultInjector(ft, rate=1.0, seed=42)
                from benchmarks.mocks import MockAnthropicClient
                mock_client = MockAnthropicClient(default_model=model, fault_injector=injector)

                provider = __import__('agenttelemetry', fromlist=['AgentTelemetryProvider']).AgentTelemetryProvider(
                    service_name='ablation',
                    privacy_level=__import__('agenttelemetry.core.privacy', fromlist=['PrivacyLevel']).PrivacyLevel.FULL,
                )
                json_exporter = provider.add_json_exporter(os.devnull)
                provider.setup(set_global=False)

                from benchmarks.apps.custom_agent.app import run_custom_agent
                try:
                    run_custom_agent(mock_client=mock_client, provider=provider, model=model, max_iterations=5, fault_injector=injector)
                except Exception:
                    pass

                exported = json_exporter.get_exported_spans()
                ground_truth = injector.get_ground_truth()

                # Strip the span kind
                stripped = _strip_span_kind(exported, kind)

                # Re-analyze
                detected, _, _, _ = _analyze_traces(stripped, ft, ground_truth)
                fdrs.append(1.0 if detected else 0.0)

                provider.shutdown()

            fdr_without = sum(fdrs) / len(fdrs)
            fdr_with = baseline_fdr[ft.value]
            delta = fdr_with - fdr_without

            # Classify necessity
            if delta > 0.5:
                necessity = "required"
            elif delta > 0.0:
                necessity = "helpful"
            else:
                necessity = "unused"

            ablation_results.append(AblationResult(
                removed_kind=kind,
                fault_type=ft.value,
                fdr_with=fdr_with,
                fdr_without=fdr_without,
                fdr_delta=delta,
                necessity=necessity,
            ))

            if verbose and delta > 0:
                print(f"  {ft.value:>22}: FDR {fdr_with:.3f} → {fdr_without:.3f} (Δ={delta:+.3f}) [{necessity}]")

    # Write results
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["removed_kind", "fault_type", "fdr_with", "fdr_without", "fdr_delta", "necessity"])
        for r in ablation_results:
            writer.writerow([r.removed_kind, r.fault_type, f"{r.fdr_with:.3f}", f"{r.fdr_without:.3f}", f"{r.fdr_delta:+.3f}", r.necessity])

    if verbose:
        _print_necessity_matrix(ablation_results)
        print(f"\nResults written to {output_file}")

    return ablation_results


def _print_necessity_matrix(results: List[AblationResult]) -> None:
    """Print the necessity matrix as a formatted table."""
    print("\n" + "=" * 70)
    print("NECESSITY MATRIX: Span Kind × Fault Type")
    print("=" * 70)

    # Build matrix
    kinds = list(dict.fromkeys(r.removed_kind for r in results))
    faults = list(dict.fromkeys(r.fault_type for r in results))

    # Header
    header = f"{'Removed Kind':>15} |"
    for ft in faults:
        header += f" {ft[:8]:>8}"
    print(header)
    print("-" * len(header))

    # Rows
    symbols = {"required": "REQ", "helpful": "hlp", "unused": "  -"}
    for kind in kinds:
        row = f"{kind:>15} |"
        for ft in faults:
            match = next((r for r in results if r.removed_kind == kind and r.fault_type == ft), None)
            if match:
                row += f" {symbols[match.necessity]:>8}"
            else:
                row += f" {'?':>8}"
        print(row)

    # Summary: how many faults each kind is required/helpful for
    print()
    print("Summary:")
    for kind in kinds:
        kind_results = [r for r in results if r.removed_kind == kind]
        req = sum(1 for r in kind_results if r.necessity == "required")
        hlp = sum(1 for r in kind_results if r.necessity == "helpful")
        unu = sum(1 for r in kind_results if r.necessity == "unused")
        print(f"  {kind:>15}: required={req}, helpful={hlp}, unused={unu}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Span kind ablation study")
    parser.add_argument("--models", nargs="*", default=None, help="Models to test")
    parser.add_argument("--output", default="benchmarks/ablation_results.tsv", help="Output file")
    args = parser.parse_args()
    run_ablation(models=args.models, output_file=args.output)
