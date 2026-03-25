"""Compute false positive rate on real (clean) SWE-bench traces.

Runs all detectors on traces where NO faults were injected.
Any anomalies found are FALSE POSITIVES.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agenttelemetry.analysis import AnomalyDetector, HallucinationTracer, CostAggregator, DecisionAttributor

RESULTS_DIR = PROJECT_ROOT / "results" / "real_fpr"


def load_spans(path: Path):
    spans = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                spans.append(json.loads(line))
    return spans


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Find trace files
    candidates = [
        PROJECT_ROOT / "results" / "swebench_100" / "traces" / "swebench_100_traces.jsonl",
        PROJECT_ROOT / "results" / "swebench_case_study" / "traces" / "swebench_traces.jsonl",
    ]
    trace_file = None
    for c in candidates:
        if c.exists():
            trace_file = c
            break

    if not trace_file:
        print("ERROR: No trace file found")
        sys.exit(1)

    print(f"Loading spans from {trace_file}...")
    spans = load_spans(trace_file)
    print(f"  {len(spans)} spans loaded")

    # Group by trace
    traces = defaultdict(list)
    for s in spans:
        traces[s.get("trace_id", "")].append(s)
    n_traces = len(traces)
    print(f"  {n_traces} traces")

    # Run detectors with PRODUCTION-REALISTIC thresholds
    print("\nRunning detectors with production thresholds...")

    detector = AnomalyDetector(
        max_retries=5,        # conservative: 5 identical calls
        cost_threshold=0.50,  # $0.50 per trace
        token_growth_factor=2.0,  # 2x growth between consecutive calls
    )
    hallucination_tracer = HallucinationTracer(min_confidence=0.5)
    cost_agg = CostAggregator()
    attributor = DecisionAttributor()

    anomalies = detector.detect(spans)
    hallucinations = hallucination_tracer.analyze(spans)
    cost_report = cost_agg.analyze(spans)
    decisions = attributor.analyze(spans)

    # Count false positives per type
    fp_by_type = defaultdict(int)
    for a in anomalies:
        fp_by_type[a.anomaly_type.value] += 1

    print(f"\n=== FALSE POSITIVE ANALYSIS ===")
    print(f"Traces analyzed: {n_traces}")
    print(f"Total spans: {len(spans)}")
    print(f"\nAnomalies (false positives): {len(anomalies)}")
    for atype, count in sorted(fp_by_type.items()):
        print(f"  {atype}: {count}")
    print(f"\nHallucination candidates (false positives): {len(hallucinations)}")

    fpr_anomaly = len(anomalies) / n_traces if n_traces > 0 else 0
    fpr_hallucination = len(hallucinations) / n_traces if n_traces > 0 else 0

    print(f"\nFPR (anomaly): {fpr_anomaly:.4f} ({len(anomalies)}/{n_traces} traces)")
    print(f"FPR (hallucination): {fpr_hallucination:.4f} ({len(hallucinations)}/{n_traces} traces)")
    print(f"FPR (combined): {(len(anomalies) + len(hallucinations)) / n_traces:.4f}")

    # Detail
    if anomalies:
        print(f"\nFalse positive details:")
        for a in anomalies:
            print(f"  [{a.severity}] {a.anomaly_type.value}: {a.description[:80]}")

    results = {
        "trace_file": str(trace_file),
        "n_traces": n_traces,
        "n_spans": len(spans),
        "thresholds": {
            "max_retries": 5,
            "cost_threshold": 0.50,
            "token_growth_factor": 2.0,
            "hallucination_min_confidence": 0.5,
        },
        "anomalies_detected": len(anomalies),
        "anomaly_types": dict(fp_by_type),
        "hallucination_candidates": len(hallucinations),
        "fpr_anomaly": round(fpr_anomaly, 4),
        "fpr_hallucination": round(fpr_hallucination, 4),
        "fpr_combined": round((len(anomalies) + len(hallucinations)) / max(n_traces, 1), 4),
    }

    with open(RESULTS_DIR / "fpr_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {RESULTS_DIR / 'fpr_results.json'}")


if __name__ == "__main__":
    main()
