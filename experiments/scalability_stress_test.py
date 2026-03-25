"""Scalability stress test for AgentTelemetry.

Goes beyond microbenchmarks to answer VLDB-style questions:

1. Concurrent trace pressure — 100 threads, each producing 20-50 spans
   across all 9 kinds.  Measures: total throughput (spans/sec),
   p50/p95/p99 span-creation latency under contention, memory growth.

2. Long-running agent simulation — Single trace with 1,000+ spans.
   Measures: memory growth over time, BatchSpanProcessor backpressure,
   span-creation latency degradation over the trace lifetime.

3. Export pipeline stress — JSON exporter writing to disk under load.
   Measures: write throughput, file size growth, whether the exporter
   blocks span creation.

Results saved to results/scalability/.
"""

from __future__ import annotations

import json
import os
import random
import resource
import statistics
import sys
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

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
from agenttelemetry.core.exporters import AgentTelemetryJSONExporter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NUM_CONCURRENT_TRACES = 100        # threads for Test 1
SPANS_PER_TRACE_MIN = 20           # min spans per concurrent trace
SPANS_PER_TRACE_MAX = 50           # max spans per concurrent trace
LONG_TRACE_SPANS = 1_200           # spans for Test 2
EXPORT_STRESS_SPANS = 10_000       # spans for Test 3
WARMUP_SPANS = 50                  # warm-up per test

ALL_KINDS = sorted(AgentSpanKind._ALL)

# Representative attributes for each span kind
SPAN_ATTRS: Dict[str, Dict[str, Any]] = {
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


def _pick_random_kind() -> Tuple[str, Dict[str, Any]]:
    """Pick a random span kind and its representative attributes."""
    kind = random.choice(ALL_KINDS)
    return kind, SPAN_ATTRS[kind]


def _get_rss_mb() -> float:
    """Get current process RSS in MB (macOS/Linux)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in bytes on macOS, kilobytes on Linux
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024 * 1024)
    return usage.ru_maxrss / 1024


# =========================================================================
# Test 1: Concurrent Trace Pressure
# =========================================================================

def _worker_trace(
    thread_id: int,
    provider: TracerProvider,
    n_spans: int,
    latencies: List[float],
    lock: threading.Lock,
) -> int:
    """Worker function for one concurrent trace.

    Returns the number of spans created.
    """
    tracer = provider.get_tracer(f"stress-thread-{thread_id}")
    local_lats: List[float] = []

    # Create a root AGENT span, then nest children
    kind, attrs = AgentSpanKind.AGENT, SPAN_ATTRS[AgentSpanKind.AGENT]
    t0 = time.perf_counter_ns()
    with start_agent_span(f"agent-{thread_id}", kind, tracer=tracer, attributes=attrs) as root:
        t1 = time.perf_counter_ns()
        local_lats.append((t1 - t0) / 1_000)  # ns -> us

        for i in range(n_spans - 1):
            child_kind, child_attrs = _pick_random_kind()
            t0 = time.perf_counter_ns()
            with start_agent_span(
                f"span-{thread_id}-{i}",
                child_kind,
                tracer=tracer,
                attributes=child_attrs,
            ):
                pass
            t1 = time.perf_counter_ns()
            local_lats.append((t1 - t0) / 1_000)

    with lock:
        latencies.extend(local_lats)
    return n_spans


def test_concurrent_pressure(results_dir: Path) -> Dict[str, Any]:
    """Test 1: 100 concurrent traces with 20-50 spans each."""
    print("\n" + "=" * 70)
    print("TEST 1: Concurrent Trace Pressure")
    print(f"  {NUM_CONCURRENT_TRACES} threads, {SPANS_PER_TRACE_MIN}-{SPANS_PER_TRACE_MAX} spans each")
    print("=" * 70)

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Warm-up
    tracer = provider.get_tracer("warmup")
    for i in range(WARMUP_SPANS):
        kind, attrs = _pick_random_kind()
        with start_agent_span(f"warm-{i}", kind, tracer=tracer, attributes=attrs):
            pass
    exporter.clear()

    all_latencies: List[float] = []
    lock = threading.Lock()
    spans_per_thread = [
        random.randint(SPANS_PER_TRACE_MIN, SPANS_PER_TRACE_MAX)
        for _ in range(NUM_CONCURRENT_TRACES)
    ]
    total_spans_planned = sum(spans_per_thread)

    rss_before = _get_rss_mb()
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=NUM_CONCURRENT_TRACES) as pool:
        futures = [
            pool.submit(
                _worker_trace, tid, provider, spans_per_thread[tid],
                all_latencies, lock,
            )
            for tid in range(NUM_CONCURRENT_TRACES)
        ]
        total_created = sum(f.result() for f in as_completed(futures))

    wall_end = time.perf_counter()
    wall_sec = wall_end - wall_start

    snap_after = tracemalloc.take_snapshot()
    tracemalloc.stop()
    rss_after = _get_rss_mb()

    mem_stats = snap_after.compare_to(snap_before, "lineno")
    mem_growth_bytes = sum(s.size_diff for s in mem_stats if s.size_diff > 0)

    arr = np.array(all_latencies)
    p50 = float(np.percentile(arr, 50))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))
    mean_lat = float(np.mean(arr))
    throughput = total_created / wall_sec

    result = {
        "test": "concurrent_trace_pressure",
        "num_threads": NUM_CONCURRENT_TRACES,
        "total_spans": total_created,
        "wall_clock_sec": round(wall_sec, 3),
        "throughput_spans_per_sec": round(throughput, 0),
        "latency_p50_us": round(p50, 1),
        "latency_p95_us": round(p95, 1),
        "latency_p99_us": round(p99, 1),
        "latency_mean_us": round(mean_lat, 1),
        "memory_growth_mb": round(mem_growth_bytes / (1024 * 1024), 2),
        "rss_before_mb": round(rss_before, 1),
        "rss_after_mb": round(rss_after, 1),
    }

    print(f"\n  Total spans created:  {total_created:,}")
    print(f"  Wall-clock time:      {wall_sec:.3f} s")
    print(f"  Throughput:           {throughput:,.0f} spans/sec")
    print(f"  Latency p50:          {p50:.1f} us")
    print(f"  Latency p95:          {p95:.1f} us")
    print(f"  Latency p99:          {p99:.1f} us")
    print(f"  Memory growth:        {mem_growth_bytes / (1024 * 1024):.2f} MB")

    provider.shutdown()
    return result


# =========================================================================
# Test 2: Long-Running Agent Simulation
# =========================================================================

def test_long_running_agent(results_dir: Path) -> Dict[str, Any]:
    """Test 2: Single trace with 1,200 spans — simulates a long agent run."""
    print("\n" + "=" * 70)
    print("TEST 2: Long-Running Agent Simulation")
    print(f"  Single trace, {LONG_TRACE_SPANS:,} spans")
    print("=" * 70)

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    # Use BatchSpanProcessor to test backpressure
    batch_processor = BatchSpanProcessor(
        exporter,
        max_queue_size=2048,
        schedule_delay_millis=500,
        max_export_batch_size=512,
    )
    provider.add_span_processor(batch_processor)
    tracer = provider.get_tracer("long-agent")

    # Warm-up
    for i in range(WARMUP_SPANS):
        kind, attrs = _pick_random_kind()
        with start_agent_span(f"warm-{i}", kind, tracer=tracer, attributes=attrs):
            pass

    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    latencies_us: List[float] = []
    checkpoints: List[Dict[str, Any]] = []
    checkpoint_interval = LONG_TRACE_SPANS // 10  # 10 checkpoints

    rss_before = _get_rss_mb()
    wall_start = time.perf_counter()

    # Create root agent span
    root_kind = AgentSpanKind.AGENT
    root_attrs = SPAN_ATTRS[root_kind]
    with start_agent_span("long-agent-root", root_kind, tracer=tracer, attributes=root_attrs):
        for i in range(LONG_TRACE_SPANS):
            kind, attrs = _pick_random_kind()
            t0 = time.perf_counter_ns()
            with start_agent_span(f"step-{i}", kind, tracer=tracer, attributes=attrs):
                pass
            t1 = time.perf_counter_ns()
            lat = (t1 - t0) / 1_000
            latencies_us.append(lat)

            # Record checkpoint every 10%
            if (i + 1) % checkpoint_interval == 0:
                pct = (i + 1) * 100 // LONG_TRACE_SPANS
                snap_now = tracemalloc.take_snapshot()
                stats_now = snap_now.compare_to(snap_before, "lineno")
                mem_now = sum(s.size_diff for s in stats_now if s.size_diff > 0)
                recent_lats = latencies_us[-checkpoint_interval:]
                checkpoints.append({
                    "progress_pct": pct,
                    "spans_created": i + 1,
                    "mem_growth_mb": round(mem_now / (1024 * 1024), 3),
                    "recent_p50_us": round(float(np.percentile(recent_lats, 50)), 1),
                    "recent_p99_us": round(float(np.percentile(recent_lats, 99)), 1),
                })

    wall_end = time.perf_counter()
    wall_sec = wall_end - wall_start

    # Force flush and wait
    batch_processor.force_flush(timeout_millis=10_000)

    snap_after = tracemalloc.take_snapshot()
    tracemalloc.stop()
    rss_after = _get_rss_mb()

    mem_stats = snap_after.compare_to(snap_before, "lineno")
    total_mem_growth = sum(s.size_diff for s in mem_stats if s.size_diff > 0)

    exported_count = len(exporter.get_finished_spans())

    arr = np.array(latencies_us)
    # First 10% vs last 10% to check degradation
    first_10 = arr[:LONG_TRACE_SPANS // 10]
    last_10 = arr[-LONG_TRACE_SPANS // 10:]

    result = {
        "test": "long_running_agent",
        "total_spans": LONG_TRACE_SPANS,
        "wall_clock_sec": round(wall_sec, 3),
        "throughput_spans_per_sec": round(LONG_TRACE_SPANS / wall_sec, 0),
        "latency_p50_us": round(float(np.percentile(arr, 50)), 1),
        "latency_p95_us": round(float(np.percentile(arr, 95)), 1),
        "latency_p99_us": round(float(np.percentile(arr, 99)), 1),
        "first_10pct_p50_us": round(float(np.percentile(first_10, 50)), 1),
        "first_10pct_p99_us": round(float(np.percentile(first_10, 99)), 1),
        "last_10pct_p50_us": round(float(np.percentile(last_10, 50)), 1),
        "last_10pct_p99_us": round(float(np.percentile(last_10, 99)), 1),
        "latency_degradation_p50_pct": round(
            (float(np.percentile(last_10, 50)) - float(np.percentile(first_10, 50)))
            / float(np.percentile(first_10, 50)) * 100, 1
        ),
        "memory_growth_mb": round(total_mem_growth / (1024 * 1024), 2),
        "batch_processor_exported": exported_count,
        "batch_processor_backpressure": exported_count < LONG_TRACE_SPANS,
        "checkpoints": checkpoints,
    }

    print(f"\n  Total spans:             {LONG_TRACE_SPANS:,}")
    print(f"  Wall-clock time:         {wall_sec:.3f} s")
    print(f"  Throughput:              {LONG_TRACE_SPANS / wall_sec:,.0f} spans/sec")
    print(f"  Latency p50:             {float(np.percentile(arr, 50)):.1f} us")
    print(f"  Latency p99:             {float(np.percentile(arr, 99)):.1f} us")
    print(f"  First 10% p50:           {float(np.percentile(first_10, 50)):.1f} us")
    print(f"  Last 10% p50:            {float(np.percentile(last_10, 50)):.1f} us")
    print(f"  Latency degradation:     {result['latency_degradation_p50_pct']:.1f}%")
    print(f"  Memory growth:           {total_mem_growth / (1024 * 1024):.2f} MB")
    print(f"  BatchProcessor exported: {exported_count} / {LONG_TRACE_SPANS}")
    print(f"  Backpressure observed:   {result['batch_processor_backpressure']}")

    print(f"\n  {'Progress':>10} {'Spans':>8} {'Mem (MB)':>10} {'p50 (us)':>10} {'p99 (us)':>10}")
    print("  " + "-" * 52)
    for cp in checkpoints:
        print(f"  {cp['progress_pct']:>9}% {cp['spans_created']:>8,} "
              f"{cp['mem_growth_mb']:>10.3f} {cp['recent_p50_us']:>10.1f} {cp['recent_p99_us']:>10.1f}")

    provider.shutdown()
    return result


# =========================================================================
# Test 3: Export Pipeline Stress
# =========================================================================

def test_export_pipeline(results_dir: Path) -> Dict[str, Any]:
    """Test 3: JSON exporter stress — measure disk write throughput and blocking."""
    print("\n" + "=" * 70)
    print("TEST 3: Export Pipeline Stress")
    print(f"  {EXPORT_STRESS_SPANS:,} spans written to JSON exporter")
    print("=" * 70)

    json_path = results_dir / "stress_export.jsonl"
    if json_path.exists():
        json_path.unlink()

    json_exporter = AgentTelemetryJSONExporter(file_path=str(json_path))
    provider = TracerProvider()
    # Use SimpleSpanProcessor so export happens inline (worst case for blocking)
    provider.add_span_processor(SimpleSpanProcessor(json_exporter))
    tracer = provider.get_tracer("export-stress")

    # Also set up a non-exporting baseline for comparison
    baseline_provider = TracerProvider()
    baseline_exporter = InMemorySpanExporter()
    baseline_provider.add_span_processor(SimpleSpanProcessor(baseline_exporter))
    baseline_tracer = baseline_provider.get_tracer("baseline")

    # Warm-up both
    for i in range(WARMUP_SPANS):
        kind, attrs = _pick_random_kind()
        with start_agent_span(f"warm-{i}", kind, tracer=tracer, attributes=attrs):
            pass
        with start_agent_span(f"warm-{i}", kind, tracer=baseline_tracer, attributes=attrs):
            pass
    # Clear the export file after warmup
    if json_path.exists():
        json_path.unlink()
    json_exporter._spans.clear()
    baseline_exporter.clear()

    # --- Measure baseline (in-memory only) ---
    baseline_lats: List[float] = []
    wall_start = time.perf_counter()
    for i in range(EXPORT_STRESS_SPANS):
        kind, attrs = _pick_random_kind()
        t0 = time.perf_counter_ns()
        with start_agent_span(f"b-{i}", kind, tracer=baseline_tracer, attributes=attrs):
            pass
        t1 = time.perf_counter_ns()
        baseline_lats.append((t1 - t0) / 1_000)
    baseline_wall = time.perf_counter() - wall_start

    # --- Measure JSON exporter ---
    export_lats: List[float] = []
    file_size_checkpoints: List[Dict[str, Any]] = []
    checkpoint_interval = EXPORT_STRESS_SPANS // 10

    wall_start = time.perf_counter()
    for i in range(EXPORT_STRESS_SPANS):
        kind, attrs = _pick_random_kind()
        t0 = time.perf_counter_ns()
        with start_agent_span(f"e-{i}", kind, tracer=tracer, attributes=attrs):
            pass
        t1 = time.perf_counter_ns()
        export_lats.append((t1 - t0) / 1_000)

        if (i + 1) % checkpoint_interval == 0:
            fsize = json_path.stat().st_size if json_path.exists() else 0
            file_size_checkpoints.append({
                "spans_written": i + 1,
                "file_size_mb": round(fsize / (1024 * 1024), 3),
            })
    export_wall = time.perf_counter() - wall_start

    final_size = json_path.stat().st_size if json_path.exists() else 0

    b_arr = np.array(baseline_lats)
    e_arr = np.array(export_lats)

    blocking_overhead_pct = (
        (float(np.median(e_arr)) - float(np.median(b_arr)))
        / float(np.median(b_arr)) * 100
    )

    result = {
        "test": "export_pipeline_stress",
        "total_spans": EXPORT_STRESS_SPANS,
        "baseline_wall_sec": round(baseline_wall, 3),
        "export_wall_sec": round(export_wall, 3),
        "baseline_throughput_sps": round(EXPORT_STRESS_SPANS / baseline_wall, 0),
        "export_throughput_sps": round(EXPORT_STRESS_SPANS / export_wall, 0),
        "baseline_p50_us": round(float(np.percentile(b_arr, 50)), 1),
        "baseline_p95_us": round(float(np.percentile(b_arr, 95)), 1),
        "baseline_p99_us": round(float(np.percentile(b_arr, 99)), 1),
        "export_p50_us": round(float(np.percentile(e_arr, 50)), 1),
        "export_p95_us": round(float(np.percentile(e_arr, 95)), 1),
        "export_p99_us": round(float(np.percentile(e_arr, 99)), 1),
        "blocking_overhead_p50_pct": round(blocking_overhead_pct, 1),
        "final_file_size_mb": round(final_size / (1024 * 1024), 3),
        "bytes_per_span": round(final_size / EXPORT_STRESS_SPANS, 0),
        "write_throughput_mb_per_sec": round(
            (final_size / (1024 * 1024)) / export_wall, 2
        ),
        "file_size_checkpoints": file_size_checkpoints,
    }

    print(f"\n  {'Metric':<30} {'Baseline':>12} {'JSON Export':>12}")
    print("  " + "-" * 56)
    print(f"  {'Wall-clock (s)':<30} {baseline_wall:>12.3f} {export_wall:>12.3f}")
    print(f"  {'Throughput (sp/s)':<30} {EXPORT_STRESS_SPANS / baseline_wall:>12,.0f} "
          f"{EXPORT_STRESS_SPANS / export_wall:>12,.0f}")
    print(f"  {'p50 latency (us)':<30} {float(np.percentile(b_arr, 50)):>12.1f} "
          f"{float(np.percentile(e_arr, 50)):>12.1f}")
    print(f"  {'p95 latency (us)':<30} {float(np.percentile(b_arr, 95)):>12.1f} "
          f"{float(np.percentile(e_arr, 95)):>12.1f}")
    print(f"  {'p99 latency (us)':<30} {float(np.percentile(b_arr, 99)):>12.1f} "
          f"{float(np.percentile(e_arr, 99)):>12.1f}")
    print(f"\n  Blocking overhead (p50):     {blocking_overhead_pct:.1f}%")
    print(f"  Final file size:             {final_size / (1024 * 1024):.3f} MB")
    print(f"  Bytes per span:              {final_size / EXPORT_STRESS_SPANS:.0f}")
    print(f"  Write throughput:            {(final_size / (1024 * 1024)) / export_wall:.2f} MB/s")

    print(f"\n  {'Spans':>10} {'File Size (MB)':>15}")
    print("  " + "-" * 27)
    for cp in file_size_checkpoints:
        print(f"  {cp['spans_written']:>10,} {cp['file_size_mb']:>15.3f}")

    # Clean up the stress file
    provider.shutdown()
    baseline_provider.shutdown()
    return result


# =========================================================================
# Summary & Report
# =========================================================================

def print_summary_table(r1: Dict, r2: Dict, r3: Dict) -> str:
    """Print and return a summary table of all three tests."""
    lines = []
    lines.append("")
    lines.append("=" * 78)
    lines.append("SCALABILITY STRESS TEST — SUMMARY")
    lines.append("=" * 78)

    header = (
        f"{'Test':<32} {'Spans':>8} {'Tput (sp/s)':>12} "
        f"{'p50 (us)':>10} {'p95 (us)':>10} {'p99 (us)':>10}"
    )
    lines.append(header)
    lines.append("-" * 78)

    rows = [
        ("1. Concurrent (100 threads)",
         r1["total_spans"],
         r1["throughput_spans_per_sec"],
         r1["latency_p50_us"],
         r1["latency_p95_us"],
         r1["latency_p99_us"]),
        ("2. Long-running (1 trace)",
         r2["total_spans"],
         r2["throughput_spans_per_sec"],
         r2["latency_p50_us"],
         r2["latency_p95_us"],
         r2["latency_p99_us"]),
        ("3a. Export baseline (in-mem)",
         r3["total_spans"],
         r3["baseline_throughput_sps"],
         r3["baseline_p50_us"],
         r3["baseline_p95_us"],
         r3["baseline_p99_us"]),
        ("3b. Export JSON (disk)",
         r3["total_spans"],
         r3["export_throughput_sps"],
         r3["export_p50_us"],
         r3["export_p95_us"],
         r3["export_p99_us"]),
    ]

    for name, spans, tput, p50, p95, p99 in rows:
        lines.append(
            f"{name:<32} {spans:>8,} {tput:>12,.0f} "
            f"{p50:>10.1f} {p95:>10.1f} {p99:>10.1f}"
        )

    lines.append("-" * 78)
    lines.append("")
    lines.append("Additional Findings:")
    lines.append(f"  Concurrent memory growth:       {r1['memory_growth_mb']:.2f} MB "
                 f"({r1['total_spans']:,} spans)")
    lines.append(f"  Long-run latency degradation:   {r2['latency_degradation_p50_pct']:.1f}% "
                 f"(first-10% vs last-10% p50)")
    lines.append(f"  Long-run memory growth:         {r2['memory_growth_mb']:.2f} MB "
                 f"({r2['total_spans']:,} spans)")
    bp = "yes" if r2["batch_processor_backpressure"] else "no"
    lines.append(f"  BatchProcessor backpressure:    {bp} "
                 f"(exported {r2['batch_processor_exported']}/{r2['total_spans']})")
    lines.append(f"  JSON export blocking overhead:  {r3['blocking_overhead_p50_pct']:.1f}% "
                 f"(p50 vs in-memory baseline)")
    lines.append(f"  JSON export file growth:        {r3['final_file_size_mb']:.3f} MB "
                 f"({r3['bytes_per_span']:.0f} B/span)")
    lines.append(f"  JSON write throughput:           {r3['write_throughput_mb_per_sec']:.2f} MB/s")
    lines.append("")

    text = "\n".join(lines)
    print(text)
    return text


def main():
    random.seed(42)  # reproducibility

    results_dir = Path(__file__).resolve().parent.parent / "results" / "scalability"
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"Results will be saved to: {results_dir}")
    print(f"Platform: {sys.platform}")
    print(f"Python: {sys.version}")

    # Run all three tests
    r1 = test_concurrent_pressure(results_dir)
    r2 = test_long_running_agent(results_dir)
    r3 = test_export_pipeline(results_dir)

    # Print summary
    summary_text = print_summary_table(r1, r2, r3)

    # Save results
    all_results = {
        "metadata": {
            "platform": sys.platform,
            "python_version": sys.version,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "concurrent_pressure": r1,
        "long_running_agent": r2,
        "export_pipeline": r3,
    }

    json_path = results_dir / "scalability_results.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Full results saved to: {json_path}")

    summary_path = results_dir / "scalability_summary.txt"
    with open(summary_path, "w") as f:
        f.write(summary_text)
    print(f"Summary saved to: {summary_path}")

    # Generate LaTeX snippet
    tex_path = results_dir / "scalability_table_snippet.tex"
    with open(tex_path, "w") as f:
        f.write("% Auto-generated scalability stress-test table\n")
        f.write("\\begin{table}[t]\n\\centering\n\\small\n")
        f.write("\\caption{Scalability stress-test results on Apple M4 Pro.\n")
        f.write("  Concurrent: 100 threads $\\times$ 20--50~spans;\n")
        f.write("  Long-running: 1{,}200 spans in a single trace with \\texttt{BatchSpanProcessor};\n")
        f.write("  Export: 10{,}000 spans via JSON-Lines exporter to disk.}\n")
        f.write("\\label{tab:scalability}\n")
        f.write("\\begin{tabular}{@{}lrrrr@{}}\n\\toprule\n")
        f.write("\\textbf{Scenario} & \\textbf{Tput (sp/s)}\n")
        f.write("  & \\textbf{p50 (\\textmu s)} & \\textbf{p95 (\\textmu s)}\n")
        f.write("  & \\textbf{p99 (\\textmu s)} \\\\\n\\midrule\n")

        rows_tex = [
            ("100-thread concurrent",
             r1["throughput_spans_per_sec"], r1["latency_p50_us"],
             r1["latency_p95_us"], r1["latency_p99_us"]),
            ("Long-running (1{,}200~spans)",
             r2["throughput_spans_per_sec"], r2["latency_p50_us"],
             r2["latency_p95_us"], r2["latency_p99_us"]),
            ("JSON export (disk)",
             r3["export_throughput_sps"], r3["export_p50_us"],
             r3["export_p95_us"], r3["export_p99_us"]),
            ("In-memory baseline",
             r3["baseline_throughput_sps"], r3["baseline_p50_us"],
             r3["baseline_p95_us"], r3["baseline_p99_us"]),
        ]
        for label, tput, p50, p95, p99 in rows_tex:
            f.write(f"{label} & {tput:,.0f} & {p50:.1f} & {p95:.1f} & {p99:.1f} \\\\\n")

        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")

    print(f"LaTeX snippet saved to: {tex_path}")


if __name__ == "__main__":
    main()
