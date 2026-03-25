"""Detailed overhead microbenchmark: per-span percentile latencies.

Produces p50, p95, p99, mean, std for each of the 9 span kinds,
plus memory-per-span and throughput figures.

Results saved to results/overhead_percentiles/.
"""

import json
import os
import statistics
import time
import tracemalloc
from pathlib import Path

import numpy as np
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agenttelemetry.core.spans import (
    AGENT_FRAMEWORK,
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_TASK,
    AgentSpanKind,
    DELEGATION_SOURCE_AGENT,
    DELEGATION_TARGET_AGENT,
    GUARDRAIL_NAME,
    GUARDRAIL_RESULT,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    LLM_TOTAL_TOKENS,
    MEMORY_KEY,
    MEMORY_OPERATION,
    PLANNING_STEP_COUNT,
    PLANNING_STRATEGY,
    REASONING_CHAIN,
    RETRIEVAL_DOC_COUNT,
    RETRIEVAL_QUERY,
    RETRIEVAL_SOURCE,
    TOOL_DESCRIPTION,
    TOOL_INPUT,
    TOOL_NAME,
    TOOL_OUTPUT,
    TOOL_STATUS,
    start_agent_span,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

N_ITERATIONS = 10_000   # per span kind
WARMUP = 100            # warm-up iterations (discarded)

# Representative attributes for each span kind (realistic payloads)
SPAN_ATTRS = {
    AgentSpanKind.LLM_CALL: {
        LLM_MODEL: "gpt-4o",
        LLM_INPUT_TOKENS: 1200,
        LLM_OUTPUT_TOKENS: 350,
        LLM_TOTAL_TOKENS: 1550,
        LLM_COST: 0.0065,
    },
    AgentSpanKind.TOOL_CALL: {
        TOOL_NAME: "web_search",
        TOOL_INPUT: '{"query": "population of France"}',
        TOOL_OUTPUT: '{"result": "67.75 million"}',
        TOOL_STATUS: "success",
        TOOL_DESCRIPTION: "Search the web for factual information",
    },
    AgentSpanKind.AGENT: {
        AGENT_NAME: "researcher",
        AGENT_FRAMEWORK: "langchain",
        AGENT_ROLE: "research-assistant",
        AGENT_TASK: "answer multi-hop questions",
    },
    AgentSpanKind.PLANNING: {
        PLANNING_STRATEGY: "chain-of-thought",
        PLANNING_STEP_COUNT: 4,
    },
    AgentSpanKind.REASONING: {
        REASONING_CHAIN: "Step 1: identify query type -> Step 2: select tool",
    },
    AgentSpanKind.RETRIEVAL: {
        RETRIEVAL_SOURCE: "vector_store",
        RETRIEVAL_QUERY: "climate change temperature rise since 1900",
        RETRIEVAL_DOC_COUNT: 5,
    },
    AgentSpanKind.GUARD_RAIL: {
        GUARDRAIL_NAME: "pii_filter",
        GUARDRAIL_RESULT: "pass",
    },
    AgentSpanKind.DELEGATION: {
        DELEGATION_SOURCE_AGENT: "planner",
        DELEGATION_TARGET_AGENT: "researcher",
    },
    AgentSpanKind.MEMORY: {
        MEMORY_OPERATION: "read",
        MEMORY_KEY: "conversation_history",
    },
}


def _make_provider():
    """Create a fresh OTel provider with in-memory exporter."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def benchmark_span_kind(kind: str, attrs: dict, n: int, warmup: int):
    """Benchmark a single span kind, returning per-iteration latencies in us."""
    provider, exporter = _make_provider()
    tracer = provider.get_tracer("bench-overhead")

    # Warm-up
    for i in range(warmup):
        with start_agent_span(f"warm-{i}", kind, tracer=tracer, attributes=attrs):
            pass
    exporter.clear()

    # Timed iterations
    latencies_us = []
    for i in range(n):
        t0 = time.perf_counter_ns()
        with start_agent_span(f"s-{i}", kind, tracer=tracer, attributes=attrs):
            pass
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1_000)  # ns -> us

    provider.shutdown()
    return latencies_us


def measure_memory_per_span(kind: str, attrs: dict, n: int = 5_000):
    """Return bytes-per-span using tracemalloc."""
    provider, exporter = _make_provider()
    tracer = provider.get_tracer("bench-mem")

    # Warm-up (outside measurement)
    for i in range(50):
        with start_agent_span(f"warm-{i}", kind, tracer=tracer, attributes=attrs):
            pass
    exporter.clear()

    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    for i in range(n):
        with start_agent_span(f"m-{i}", kind, tracer=tracer, attributes=attrs):
            pass

    snap_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snap_after.compare_to(snap_before, "lineno")
    total_increase = sum(s.size_diff for s in stats if s.size_diff > 0)
    provider.shutdown()
    return total_increase / n


def measure_throughput(kind: str, attrs: dict, duration_s: float = 2.0):
    """Measure sustained throughput (spans/sec) over a fixed window."""
    provider, exporter = _make_provider()
    tracer = provider.get_tracer("bench-tput")

    # Warm-up
    for i in range(100):
        with start_agent_span(f"warm-{i}", kind, tracer=tracer, attributes=attrs):
            pass
    exporter.clear()

    count = 0
    t_end = time.perf_counter() + duration_s
    while time.perf_counter() < t_end:
        with start_agent_span(f"t-{count}", kind, tracer=tracer, attributes=attrs):
            pass
        count += 1

    provider.shutdown()
    return count / duration_s


def main():
    results_dir = Path(__file__).resolve().parent.parent / "results" / "overhead_percentiles"
    results_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    all_latencies_us = []  # aggregate across all span kinds

    print(f"{'Span Kind':<15} {'p50 (us)':>10} {'p95 (us)':>10} {'p99 (us)':>10} "
          f"{'mean (us)':>10} {'std (us)':>10} {'mem (B)':>10} {'tput (sp/s)':>12}")
    print("-" * 95)

    for kind in sorted(AgentSpanKind._ALL):
        attrs = SPAN_ATTRS[kind]

        # Latency
        lats = benchmark_span_kind(kind, attrs, N_ITERATIONS, WARMUP)
        arr = np.array(lats)
        p50 = float(np.percentile(arr, 50))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
        mean = float(np.mean(arr))
        std = float(np.std(arr))

        # Memory
        mem_bytes = measure_memory_per_span(kind, attrs)

        # Throughput
        tput = measure_throughput(kind, attrs)

        all_latencies_us.extend(lats)

        row = {
            "span_kind": kind,
            "n": N_ITERATIONS,
            "p50_us": round(p50, 2),
            "p95_us": round(p95, 2),
            "p99_us": round(p99, 2),
            "mean_us": round(mean, 2),
            "std_us": round(std, 2),
            "memory_bytes_per_span": round(mem_bytes, 1),
            "throughput_spans_per_sec": round(tput, 0),
        }
        all_results[kind] = row

        print(f"{kind:<15} {p50:10.1f} {p95:10.1f} {p99:10.1f} "
              f"{mean:10.1f} {std:10.1f} {mem_bytes:10.1f} {tput:12.0f}")

    # Aggregate across all 9 kinds
    agg = np.array(all_latencies_us)
    agg_row = {
        "span_kind": "ALL (aggregate)",
        "n": len(all_latencies_us),
        "p50_us": round(float(np.percentile(agg, 50)), 2),
        "p95_us": round(float(np.percentile(agg, 95)), 2),
        "p99_us": round(float(np.percentile(agg, 99)), 2),
        "mean_us": round(float(np.mean(agg)), 2),
        "std_us": round(float(np.std(agg)), 2),
    }
    all_results["AGGREGATE"] = agg_row

    print("-" * 95)
    print(f"{'AGGREGATE':<15} {agg_row['p50_us']:10.1f} {agg_row['p95_us']:10.1f} "
          f"{agg_row['p99_us']:10.1f} {agg_row['mean_us']:10.1f} {agg_row['std_us']:10.1f}")

    # Save
    out_path = results_dir / "overhead_percentiles.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Also save a LaTeX-ready snippet
    tex_path = results_dir / "overhead_table_snippet.tex"
    with open(tex_path, "w") as f:
        f.write("% Auto-generated overhead percentile table\n")
        f.write("\\begin{table}[t]\n\\centering\n\\small\n")
        f.write("\\caption{Span creation latency (\\textmu s) over 10{,}000 iterations per kind.}\n")
        f.write("\\label{tab:overhead}\n")
        f.write("\\begin{tabular}{@{}lrrrrr@{}}\n\\toprule\n")
        f.write("\\textbf{Span Kind} & \\textbf{p50} & \\textbf{p95} & \\textbf{p99} "
                "& \\textbf{Mean} & \\textbf{Std} \\\\\n\\midrule\n")
        for kind in sorted(AgentSpanKind._ALL):
            r = all_results[kind]
            kname = kind.replace("_", "\\_")
            f.write(f"{kname} & {r['p50_us']:.1f} & {r['p95_us']:.1f} & {r['p99_us']:.1f} "
                    f"& {r['mean_us']:.1f} & {r['std_us']:.1f} \\\\\n")
        f.write("\\midrule\n")
        r = agg_row
        f.write(f"All (aggregate) & {r['p50_us']:.1f} & {r['p95_us']:.1f} & {r['p99_us']:.1f} "
                f"& {r['mean_us']:.1f} & {r['std_us']:.1f} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    print(f"LaTeX snippet saved to {tex_path}")


if __name__ == "__main__":
    main()
