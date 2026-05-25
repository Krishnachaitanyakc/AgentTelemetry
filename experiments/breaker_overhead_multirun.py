"""Multi-run circuit-breaker activation overhead, with CIs.

Compares per-span latency with vs without a four-policy AgentCircuitBreaker
installed. Repeats the whole experiment 5 times to compute across-run
confidence intervals on the +X us overhead claim.

Each run: 10,000 LLM_CALL spans per configuration, attribute payload
sufficient to drive all four policies (cost, input tokens, tool name,
tool input).

Result: results/overhead_percentiles/breaker_multirun.json
"""

import json
import time
from pathlib import Path

import numpy as np
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agenttelemetry.core.spans import (
    AgentSpanKind,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    LLM_TOTAL_TOKENS,
    TOOL_INPUT,
    TOOL_NAME,
    start_agent_span,
)
from agenttelemetry.runtime.circuit_breaker import (
    AgentCircuitBreaker,
    CircuitAction,
)

N_PER_CONFIG = 10_000
WARMUP = 100
N_RUNS = 5


PAYLOAD = {
    LLM_MODEL: "gpt-4o",
    LLM_INPUT_TOKENS: 1200,
    LLM_OUTPUT_TOKENS: 350,
    LLM_TOTAL_TOKENS: 1550,
    LLM_COST: 0.0065,
    TOOL_NAME: "web_search",
    TOOL_INPUT: '{"query": "population of France"}',
}


def percentiles(arr):
    return {
        "p50_us": float(np.percentile(arr, 50)),
        "p95_us": float(np.percentile(arr, 95)),
        "p99_us": float(np.percentile(arr, 99)),
        "mean_us": float(np.mean(arr)),
        "std_us": float(np.std(arr)),
    }


def ci95(values):
    if len(values) < 2:
        return {"mean": float(values[0]), "ci_lo": float(values[0]),
                "ci_hi": float(values[0]), "min": float(values[0]),
                "max": float(values[0])}
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    n = len(values)
    half = 1.96 * std / (n ** 0.5)
    return {"mean": mean, "ci_lo": mean - half, "ci_hi": mean + half,
            "min": float(min(values)), "max": float(max(values))}


def install_breaker(provider):
    # All policies installed with no callback, so action defaults to LOG.
    # Thresholds set high so policies never fire during the benchmark
    # (we are measuring evaluation overhead, not firing overhead).
    breaker = AgentCircuitBreaker()
    breaker.configure_cost_explosion(threshold=1e9)
    breaker.configure_reasoning_loop(max_repeats=10_000)
    breaker.configure_context_overflow(growth_factor=1e9)
    breaker.configure_delegation_cycle()
    provider.add_span_processor(breaker)
    return breaker


def run_one(with_breaker):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    if with_breaker:
        install_breaker(provider)
    tracer = provider.get_tracer("bench-breaker")

    for i in range(WARMUP):
        with start_agent_span(f"warm-{i}", AgentSpanKind.LLM_CALL,
                              tracer=tracer, attributes=PAYLOAD):
            pass
    exporter.clear()

    lats = []
    for i in range(N_PER_CONFIG):
        t0 = time.perf_counter_ns()
        with start_agent_span(f"s-{i}", AgentSpanKind.LLM_CALL,
                              tracer=tracer, attributes=PAYLOAD):
            pass
        t1 = time.perf_counter_ns()
        lats.append((t1 - t0) / 1_000)
    provider.shutdown()
    return percentiles(np.array(lats))


def main():
    no_breaker_runs = []
    with_breaker_runs = []
    overhead_p50 = []
    overhead_p99 = []
    overhead_mean = []

    print(f"Running {N_RUNS} independent runs, {N_PER_CONFIG} spans each")
    for r in range(N_RUNS):
        nb = run_one(with_breaker=False)
        wb = run_one(with_breaker=True)
        no_breaker_runs.append(nb)
        with_breaker_runs.append(wb)
        d50 = wb["p50_us"] - nb["p50_us"]
        d99 = wb["p99_us"] - nb["p99_us"]
        dmean = wb["mean_us"] - nb["mean_us"]
        overhead_p50.append(d50)
        overhead_p99.append(d99)
        overhead_mean.append(dmean)
        rel = 100.0 * d50 / nb["p50_us"]
        print(f"  run {r + 1}: no_breaker p50={nb['p50_us']:.2f} "
              f"with_breaker p50={wb['p50_us']:.2f} "
              f"delta_p50={d50:+.2f}us ({rel:+.1f}%) "
              f"delta_p99={d99:+.2f}us")

    summary = {
        "n_per_config": N_PER_CONFIG,
        "num_runs": N_RUNS,
        "no_breaker_per_run": no_breaker_runs,
        "with_breaker_per_run": with_breaker_runs,
        "no_breaker": {
            "p50_us": ci95([r["p50_us"] for r in no_breaker_runs]),
            "p95_us": ci95([r["p95_us"] for r in no_breaker_runs]),
            "p99_us": ci95([r["p99_us"] for r in no_breaker_runs]),
            "mean_us": ci95([r["mean_us"] for r in no_breaker_runs]),
        },
        "with_breaker": {
            "p50_us": ci95([r["p50_us"] for r in with_breaker_runs]),
            "p95_us": ci95([r["p95_us"] for r in with_breaker_runs]),
            "p99_us": ci95([r["p99_us"] for r in with_breaker_runs]),
            "mean_us": ci95([r["mean_us"] for r in with_breaker_runs]),
        },
        "overhead": {
            "delta_p50_us": ci95(overhead_p50),
            "delta_p99_us": ci95(overhead_p99),
            "delta_mean_us": ci95(overhead_mean),
        },
    }

    out = (Path(__file__).resolve().parent.parent / "results"
           / "overhead_percentiles" / "breaker_multirun.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)

    nb50 = summary["no_breaker"]["p50_us"]
    wb50 = summary["with_breaker"]["p50_us"]
    d50 = summary["overhead"]["delta_p50_us"]
    print(f"\nNo breaker p50 (mean across runs): {nb50['mean']:.2f}us "
          f"95% CI [{nb50['ci_lo']:.2f}, {nb50['ci_hi']:.2f}]")
    print(f"With breaker p50 (mean across runs): {wb50['mean']:.2f}us "
          f"95% CI [{wb50['ci_lo']:.2f}, {wb50['ci_hi']:.2f}]")
    print(f"Breaker overhead p50 (delta, mean): {d50['mean']:+.2f}us "
          f"95% CI [{d50['ci_lo']:+.2f}, {d50['ci_hi']:+.2f}]")
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
