"""Multi-run wrapper: runs the per-span microbenchmark 3 times to compute
across-run confidence intervals on p50/p95/p99.

Also runs a Batch-flush-isolation experiment to validate the
"BatchSpanProcessor background flush" explanation for the DELEGATION p99
anomaly, by repeating the DELEGATION benchmark with a SimpleSpanProcessor
(no batching) and with a BatchSpanProcessor whose schedule_delay_millis is
set to 60s (so no scheduled flushes during the run).

Results saved to results/overhead_percentiles/multirun_ci.json and
results/overhead_percentiles/batch_isolation.json.
"""

import json
import statistics
import time
from pathlib import Path

import numpy as np
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agenttelemetry.core.spans import (
    AgentSpanKind,
    DELEGATION_SOURCE_AGENT,
    DELEGATION_TARGET_AGENT,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    LLM_TOTAL_TOKENS,
    start_agent_span,
)

# Reuse SPAN_ATTRS from the single-run script
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from overhead_percentiles import SPAN_ATTRS, N_ITERATIONS, WARMUP, benchmark_span_kind


def percentiles(arr):
    return {
        "p50_us": float(np.percentile(arr, 50)),
        "p95_us": float(np.percentile(arr, 95)),
        "p99_us": float(np.percentile(arr, 99)),
        "mean_us": float(np.mean(arr)),
        "std_us": float(np.std(arr)),
    }


def ci95(values):
    """Return mean and the two endpoints of a normal 95% CI on the mean of `values`."""
    if len(values) < 2:
        return {"mean": float(values[0]), "ci_lo": float(values[0]), "ci_hi": float(values[0]),
                "min": float(values[0]), "max": float(values[0])}
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    n = len(values)
    half = 1.96 * std / (n ** 0.5)
    return {"mean": mean, "ci_lo": mean - half, "ci_hi": mean + half,
            "min": float(min(values)), "max": float(max(values))}


def multirun_overhead(num_runs=3):
    """Run the overhead microbenchmark `num_runs` times and report across-run CIs
    for p50/p95/p99/mean per span kind."""
    per_kind_per_run = {kind: [] for kind in AgentSpanKind._ALL}
    aggregate_per_run = []

    for run_idx in range(num_runs):
        print(f"\n=== Run {run_idx + 1}/{num_runs} ===")
        agg = []
        for kind in sorted(AgentSpanKind._ALL):
            attrs = SPAN_ATTRS[kind]
            lats = benchmark_span_kind(kind, attrs, N_ITERATIONS, WARMUP)
            pcs = percentiles(np.array(lats))
            per_kind_per_run[kind].append(pcs)
            agg.extend(lats)
            print(f"  {kind:<15} p50={pcs['p50_us']:6.2f} p99={pcs['p99_us']:6.2f}")
        aggregate_per_run.append(percentiles(np.array(agg)))

    summary = {}
    for kind in sorted(AgentSpanKind._ALL):
        runs = per_kind_per_run[kind]
        summary[kind] = {
            "num_runs": num_runs,
            "p50_us": ci95([r["p50_us"] for r in runs]),
            "p95_us": ci95([r["p95_us"] for r in runs]),
            "p99_us": ci95([r["p99_us"] for r in runs]),
            "mean_us": ci95([r["mean_us"] for r in runs]),
            "std_us": ci95([r["std_us"] for r in runs]),
            "per_run": runs,
        }
    summary["AGGREGATE"] = {
        "num_runs": num_runs,
        "p50_us": ci95([r["p50_us"] for r in aggregate_per_run]),
        "p95_us": ci95([r["p95_us"] for r in aggregate_per_run]),
        "p99_us": ci95([r["p99_us"] for r in aggregate_per_run]),
        "mean_us": ci95([r["mean_us"] for r in aggregate_per_run]),
        "per_run": aggregate_per_run,
    }
    return summary


def isolation_delegation_batchprocessor(n=10_000, warmup=100):
    """Compare DELEGATION p50/p99/std under three processor configs.

    cfg A: SimpleSpanProcessor (no batching) - background flush impossible.
    cfg B: BatchSpanProcessor with default schedule_delay_millis (5000ms)
           - matches the conditions that produced the original p99=42.6us
           anomaly.
    cfg C: BatchSpanProcessor with schedule_delay_millis=600000 (10 min) and
           max_export_batch_size=20000 - no scheduled flush will occur
           during a 10,000-span run.
    """
    attrs = SPAN_ATTRS[AgentSpanKind.DELEGATION]

    def run_with_processor(proc_factory):
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(proc_factory(exporter))
        tracer = provider.get_tracer("bench-iso")
        for i in range(warmup):
            with start_agent_span(f"warm-{i}", AgentSpanKind.DELEGATION,
                                  tracer=tracer, attributes=attrs):
                pass
        exporter.clear()
        lats = []
        for i in range(n):
            t0 = time.perf_counter_ns()
            with start_agent_span(f"s-{i}", AgentSpanKind.DELEGATION,
                                  tracer=tracer, attributes=attrs):
                pass
            t1 = time.perf_counter_ns()
            lats.append((t1 - t0) / 1_000)
        provider.shutdown()
        return percentiles(np.array(lats))

    cfg_a = run_with_processor(lambda e: SimpleSpanProcessor(e))
    cfg_b = run_with_processor(lambda e: BatchSpanProcessor(e))
    cfg_c = run_with_processor(lambda e: BatchSpanProcessor(
        e, schedule_delay_millis=600_000, max_export_batch_size=20_000,
        max_queue_size=40_000))

    return {
        "n_per_config": n,
        "simple_span_processor": cfg_a,
        "batch_default_5000ms_delay": cfg_b,
        "batch_long_600000ms_delay": cfg_c,
    }


def main():
    results_dir = (Path(__file__).resolve().parent.parent / "results"
                   / "overhead_percentiles")
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Multi-run overhead microbenchmark (3 independent runs)")
    print("=" * 70)
    summary = multirun_overhead(num_runs=3)
    out_a = results_dir / "multirun_ci.json"
    with open(out_a, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Across-run CIs saved to {out_a}")

    agg = summary["AGGREGATE"]
    print(f"\nAGGREGATE across {agg['num_runs']} runs:")
    print(f"  p50  mean={agg['p50_us']['mean']:.2f}us "
          f"[{agg['p50_us']['min']:.2f}, {agg['p50_us']['max']:.2f}]")
    print(f"  p99  mean={agg['p99_us']['mean']:.2f}us "
          f"[{agg['p99_us']['min']:.2f}, {agg['p99_us']['max']:.2f}]")

    print("\n" + "=" * 70)
    print("DELEGATION batch-flush isolation experiment")
    print("=" * 70)
    iso = isolation_delegation_batchprocessor()
    out_b = results_dir / "batch_isolation.json"
    with open(out_b, "w") as f:
        json.dump(iso, f, indent=2)
    for label, pcs in iso.items():
        if label == "n_per_config":
            continue
        print(f"  {label:<35} p50={pcs['p50_us']:6.2f} p99={pcs['p99_us']:6.2f} "
              f"std={pcs['std_us']:6.2f}")
    print(f"\nIsolation results saved to {out_b}")


if __name__ == "__main__":
    main()
