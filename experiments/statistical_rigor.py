"""Statistical rigor experiment for AgentTelemetry evaluation.

Runs the benchmark with multiple random seeds and injection rates,
computing mean +/- std and 95% confidence intervals for FDR and FPR.

Addresses reviewer concern: "single-run results lack statistical rigor."

Usage:
    cd agenttelemetry
    PYTHONPATH=src:. .venv/bin/python3.12 experiments/statistical_rigor.py
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Ensure src and benchmarks are on sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SCRIPT_DIR)
_SRC_DIR = os.path.join(_ROOT_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from agenttelemetry import AgentTelemetryProvider
from agenttelemetry.core.privacy import PrivacyLevel
from agenttelemetry.core.spans import AGENT_SPAN_KIND

from benchmarks.faults import FaultInjector, FaultType
from benchmarks.mocks import MockAnthropicClient, MockOpenAIClient
from benchmarks.apps.custom_agent.app import run_custom_agent
from benchmarks.run_benchmarks import (
    _analyze_traces,
    _analyze_all_detectors,
    MODELS,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEEDS = [42, 123, 456, 789, 1024]
INJECTION_RATES = [0.10, 0.25, 0.50, 0.75, 1.00]
# Use 2 models (one Anthropic, one OpenAI) for each seed/rate combo
STAT_MODELS = ["claude-sonnet-4", "gpt-4o"]
FRAMEWORK = "custom"
CONDITION = "full_capture"

# All real fault types (exclude NONE which is for FP analysis)
FAULT_TYPES = [ft for ft in FaultType if ft != FaultType.NONE]


# ---------------------------------------------------------------------------
# Helper: run one benchmark with configurable seed and injection rate
# ---------------------------------------------------------------------------

def run_with_seed_and_rate(
    model: str,
    fault_type: FaultType,
    seed: int,
    injection_rate: float,
) -> Dict[str, Any]:
    """Run a single benchmark with a specific seed and injection rate.

    Returns dict with:
        fault_detected: bool
        faults_injected: int (count from ground truth)
        faults_detected: int
        fdr: float
    """
    injector = FaultInjector(fault_type, rate=injection_rate, seed=seed)

    is_anthropic = "claude" in model or "sonnet" in model or "haiku" in model or "opus" in model
    if is_anthropic:
        mock_client = MockAnthropicClient(default_model=model, fault_injector=injector)
    else:
        mock_client = MockOpenAIClient(default_model=model, fault_injector=injector)

    provider = AgentTelemetryProvider(
        service_name="stat-rigor",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(os.devnull)
    provider.setup(set_global=False)

    try:
        run_custom_agent(
            mock_client=mock_client,
            provider=provider,
            model=model,
            max_iterations=5,
            fault_injector=injector,
        )
    except Exception:
        pass

    exported_spans = json_exporter.get_exported_spans()
    ground_truth = injector.get_ground_truth()

    fault_detected, detection_correct, ttrc_ms, faults_found = _analyze_traces(
        exported_spans, fault_type, ground_truth,
    )

    provider.shutdown()

    faults_injected = 1 if ground_truth else 0
    fdr = faults_found / faults_injected if faults_injected > 0 else 1.0

    return {
        "fault_detected": fault_detected,
        "faults_injected": faults_injected,
        "faults_detected": faults_found,
        "fdr": fdr,
    }


def run_fp_with_seed(model: str, seed: int) -> Dict[str, bool]:
    """Run false-positive analysis with a specific seed (NONE fault).

    Returns dict mapping fault_type_name -> bool (fired).
    """
    injector = FaultInjector(FaultType.NONE, rate=1.0, seed=seed)

    is_anthropic = "claude" in model or "sonnet" in model or "haiku" in model or "opus" in model
    if is_anthropic:
        mock_client = MockAnthropicClient(default_model=model, fault_injector=injector)
    else:
        mock_client = MockOpenAIClient(default_model=model, fault_injector=injector)

    provider = AgentTelemetryProvider(
        service_name="stat-rigor-fp",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(os.devnull)
    provider.setup(set_global=False)

    try:
        run_custom_agent(
            mock_client=mock_client,
            provider=provider,
            model=model,
            max_iterations=5,
            fault_injector=injector,
        )
    except Exception:
        pass

    exported_spans = json_exporter.get_exported_spans()
    detector_results = _analyze_all_detectors(exported_spans, CONDITION)

    provider.shutdown()
    return detector_results


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def ci_95(values: List[float]) -> Tuple[float, float]:
    """Compute 95% CI using t-distribution approximation.

    For n=5, t_{0.025,4} = 2.776.
    """
    n = len(values)
    if n < 2:
        m = mean(values)
        return (m, m)

    # t critical values for 95% CI, two-tailed
    t_critical = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776,
                  6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262}
    t = t_critical.get(n, 1.96)  # fall back to z for large n

    m = mean(values)
    se = std(values) / math.sqrt(n)
    margin = t * se
    return (max(0.0, m - margin), min(1.0, m + margin))


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

@dataclass
class SeedResult:
    """Result from one seed x rate x fault_type combination."""
    seed: int
    injection_rate: float
    fault_type: str
    fdr: float  # averaged across models


@dataclass
class AggregateResult:
    """Aggregated statistics across seeds for one rate x fault_type."""
    injection_rate: float
    fault_type: str
    fdr_mean: float
    fdr_std: float
    fdr_ci_lo: float
    fdr_ci_hi: float
    n_seeds: int


def run_statistical_rigor(
    seeds: List[int] = SEEDS,
    injection_rates: List[float] = INJECTION_RATES,
    models: List[str] = STAT_MODELS,
    output_dir: str = "results/statistical_rigor",
    verbose: bool = True,
) -> Tuple[List[AggregateResult], List[Dict[str, Any]]]:
    """Run the full statistical rigor experiment.

    Returns:
        (aggregate_results, fp_results)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    total_runs = len(seeds) * len(injection_rates) * len(FAULT_TYPES) * len(models)
    run_count = 0
    start_time = time.time()

    if verbose:
        print("=" * 70)
        print("STATISTICAL RIGOR EXPERIMENT")
        print("=" * 70)
        print(f"Seeds:           {seeds}")
        print(f"Injection rates: {injection_rates}")
        print(f"Models:          {models}")
        print(f"Fault types:     {len(FAULT_TYPES)}")
        print(f"Total runs:      {total_runs}")
        print()

    # ------------------------------------------------------------------
    # Part 1: Multi-seed FDR across injection rates
    # ------------------------------------------------------------------
    seed_results: List[SeedResult] = []

    for rate in injection_rates:
        if verbose:
            print(f"\n--- Injection rate: {rate:.0%} ---")

        for ft in FAULT_TYPES:
            for seed in seeds:
                fdrs = []
                for model in models:
                    run_count += 1
                    result = run_with_seed_and_rate(model, ft, seed, rate)
                    fdrs.append(result["fdr"])

                avg_fdr = mean(fdrs)
                seed_results.append(SeedResult(
                    seed=seed,
                    injection_rate=rate,
                    fault_type=ft.value,
                    fdr=avg_fdr,
                ))

            if verbose and run_count % 20 == 0:
                elapsed = time.time() - start_time
                pct = run_count / total_runs * 100
                print(f"  Progress: {run_count}/{total_runs} ({pct:.0f}%) "
                      f"[{elapsed:.1f}s elapsed]")

    # ------------------------------------------------------------------
    # Aggregate: mean +/- std and 95% CI per (rate, fault_type)
    # ------------------------------------------------------------------
    aggregate_results: List[AggregateResult] = []

    for rate in injection_rates:
        for ft in FAULT_TYPES:
            fdrs = [
                sr.fdr for sr in seed_results
                if sr.injection_rate == rate and sr.fault_type == ft.value
            ]
            ci_lo, ci_hi = ci_95(fdrs)
            aggregate_results.append(AggregateResult(
                injection_rate=rate,
                fault_type=ft.value,
                fdr_mean=mean(fdrs),
                fdr_std=std(fdrs),
                fdr_ci_lo=ci_lo,
                fdr_ci_hi=ci_hi,
                n_seeds=len(fdrs),
            ))

    # ------------------------------------------------------------------
    # Part 2: False-positive analysis across seeds
    # ------------------------------------------------------------------
    if verbose:
        print(f"\n--- False-positive analysis ({len(seeds)} seeds x {len(models)} models) ---")

    fp_results: List[Dict[str, Any]] = []
    for seed in seeds:
        for model in models:
            detector_fires = run_fp_with_seed(model, seed)
            fp_count = sum(1 for v in detector_fires.values() if v)
            fp_results.append({
                "seed": seed,
                "model": model,
                "total_detectors": len(detector_fires),
                "false_positives": fp_count,
                "fpr": fp_count / len(detector_fires) if detector_fires else 0.0,
                "fired_detectors": [k for k, v in detector_fires.items() if v],
            })
            if verbose:
                print(f"  seed={seed}, model={model}: FP={fp_count}/{len(detector_fires)} "
                      f"(FPR={fp_count / len(detector_fires):.3f})")

    # Compute aggregate FPR
    all_fprs = [r["fpr"] for r in fp_results]
    fpr_mean = mean(all_fprs)
    fpr_std_val = std(all_fprs)
    fpr_ci = ci_95(all_fprs)

    # ------------------------------------------------------------------
    # Write results
    # ------------------------------------------------------------------

    # 1. Per-seed raw results
    raw_file = output_path / "raw_seed_results.tsv"
    with open(raw_file, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["seed", "injection_rate", "fault_type", "fdr"])
        for sr in seed_results:
            writer.writerow([sr.seed, f"{sr.injection_rate:.2f}", sr.fault_type, f"{sr.fdr:.3f}"])

    # 2. Aggregate results table
    agg_file = output_path / "aggregate_results.tsv"
    with open(agg_file, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["injection_rate", "fault_type", "fdr_mean", "fdr_std",
                          "fdr_ci_lo", "fdr_ci_hi", "n_seeds"])
        for ar in aggregate_results:
            writer.writerow([
                f"{ar.injection_rate:.2f}", ar.fault_type,
                f"{ar.fdr_mean:.3f}", f"{ar.fdr_std:.3f}",
                f"{ar.fdr_ci_lo:.3f}", f"{ar.fdr_ci_hi:.3f}",
                ar.n_seeds,
            ])

    # 3. Summary table: injection_rate x aggregated metrics
    summary_file = output_path / "summary_table.tsv"
    with open(summary_file, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["injection_rate", "fdr_mean", "fdr_std", "fdr_ci_95",
                          "fpr_mean", "fpr_std", "fpr_ci_95"])
        for rate in injection_rates:
            rate_results = [ar for ar in aggregate_results if ar.injection_rate == rate]
            rate_fdrs = [ar.fdr_mean for ar in rate_results]
            rate_fdr_mean = mean(rate_fdrs)
            rate_fdr_std = std(rate_fdrs)
            rate_ci = ci_95(rate_fdrs)
            writer.writerow([
                f"{rate:.2f}",
                f"{rate_fdr_mean:.3f}", f"{rate_fdr_std:.3f}",
                f"[{rate_ci[0]:.3f}, {rate_ci[1]:.3f}]",
                f"{fpr_mean:.3f}", f"{fpr_std_val:.3f}",
                f"[{fpr_ci[0]:.3f}, {fpr_ci[1]:.3f}]",
            ])

    # 4. FP analysis results
    fp_file = output_path / "false_positive_analysis.json"
    fp_summary = {
        "fpr_mean": fpr_mean,
        "fpr_std": fpr_std_val,
        "fpr_ci_95": [fpr_ci[0], fpr_ci[1]],
        "n_runs": len(fp_results),
        "per_run": fp_results,
    }
    with open(fp_file, "w") as f:
        json.dump(fp_summary, f, indent=2)

    # ------------------------------------------------------------------
    # Print summary
    # ------------------------------------------------------------------
    if verbose:
        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        print()

        # Table header
        print(f"{'Rate':>6}  {'FDR mean':>8}  {'FDR std':>7}  {'FDR 95% CI':>16}  "
              f"{'FPR mean':>8}  {'FPR 95% CI':>16}")
        print("-" * 75)

        for rate in injection_rates:
            rate_results = [ar for ar in aggregate_results if ar.injection_rate == rate]
            rate_fdrs = [ar.fdr_mean for ar in rate_results]
            rate_fdr_mean = mean(rate_fdrs)
            rate_fdr_std = std(rate_fdrs)
            rate_ci = ci_95(rate_fdrs)
            print(f"{rate:>5.0%}   {rate_fdr_mean:>8.3f}  {rate_fdr_std:>7.3f}  "
                  f"[{rate_ci[0]:.3f}, {rate_ci[1]:.3f}]  "
                  f"{fpr_mean:>8.3f}  [{fpr_ci[0]:.3f}, {fpr_ci[1]:.3f}]")

        print()
        print(f"False positive rate: {fpr_mean:.3f} +/- {fpr_std_val:.3f} "
              f"(95% CI: [{fpr_ci[0]:.3f}, {fpr_ci[1]:.3f}])")
        print()

        # Per-fault-type breakdown at 100% injection rate
        print("Per-fault-type FDR at 100% injection rate:")
        print(f"  {'Fault type':>25}  {'mean':>6}  {'std':>6}  {'95% CI':>16}")
        print("  " + "-" * 60)
        for ar in aggregate_results:
            if ar.injection_rate == 1.0:
                print(f"  {ar.fault_type:>25}  {ar.fdr_mean:>6.3f}  {ar.fdr_std:>6.3f}  "
                      f"[{ar.fdr_ci_lo:.3f}, {ar.fdr_ci_hi:.3f}]")

        print()
        print(f"Total time: {elapsed:.1f}s")
        print(f"Results written to: {output_path}/")

    return aggregate_results, fp_results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Statistical rigor experiment")
    parser.add_argument("--seeds", nargs="*", type=int, default=SEEDS,
                        help="Random seeds to use")
    parser.add_argument("--output-dir", default="results/statistical_rigor",
                        help="Output directory")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    run_statistical_rigor(
        seeds=args.seeds,
        output_dir=args.output_dir,
        verbose=not args.quiet,
    )
