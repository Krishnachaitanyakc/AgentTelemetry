#!/usr/bin/env python3
"""AgentTelemetry overhead benchmark.

Measures instrumentation overhead across seven categories:
  1. Span creation (task, llm_call, tool_call) with/without attributes
  2. Context propagation (to_carrier / from_carrier round trips)
  3. Exporter overhead (ConsoleExporter to /dev/null, JSONFileExporter to temp)
  4. Memory overhead (10,000 accumulated spans)
  5. Nested span overhead (deeply nested traces)
  6. Cost estimation overhead
  7. Metrics recording overhead (counter increments, histogram records)

Each measurement is repeated 5 times; results report mean +/- std.
No external dependencies beyond the Python standard library.

Usage:
    PYTHONPATH=src python3 benchmarks/overhead_benchmark.py
"""

from __future__ import annotations

import gc
import io
import math
import os
import sys
import tempfile
import time
from contextlib import contextmanager, redirect_stdout
from typing import Callable, List, Tuple

# ---------------------------------------------------------------------------
# Ensure src is on sys.path so the script can be run standalone
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# ---------------------------------------------------------------------------
# Import AgentTelemetry components
# ---------------------------------------------------------------------------
from agenttelemetry.core.trace import (
    AgentSpan,
    AgentSpanKind,
    AgentTracer,
    estimate_cost,
)
from agenttelemetry.core.context import AgentContext
from agenttelemetry.core.metrics import AgentMetrics
from agenttelemetry.exporters.console import ConsoleExporter
from agenttelemetry.exporters.json_file import JSONFileExporter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_ITERATIONS = 10_000   # ops per trial (except nested spans)
N_NESTED = 1_000        # nested span traces per trial
N_TRIALS = 5            # repetitions for mean/std
DEVNULL = open(os.devnull, "w")


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------
def _time_fn(fn: Callable[[], None], trials: int = N_TRIALS) -> Tuple[float, float]:
    """Run *fn* for *trials* repetitions, return (mean_seconds, std_seconds)."""
    timings: List[float] = []
    for _ in range(trials):
        gc.disable()
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        gc.enable()
        timings.append(elapsed)
    mean = sum(timings) / len(timings)
    variance = sum((t - mean) ** 2 for t in timings) / len(timings)
    std = math.sqrt(variance)
    return mean, std


# ---------------------------------------------------------------------------
# 1. Span creation overhead
# ---------------------------------------------------------------------------
def bench_span_creation_bare() -> Tuple[float, float]:
    """Create N spans (task, llm_call, tool_call) without extra attributes."""
    def run():
        tracer = AgentTracer(agent_name="bench", framework="benchmark")
        for i in range(N_ITERATIONS):
            kind_idx = i % 3
            if kind_idx == 0:
                with tracer.start_task(f"task-{i}"):
                    pass
            elif kind_idx == 1:
                # Need a task parent for llm_call
                with tracer.start_task(f"task-{i}"):
                    with tracer.start_llm_call(model="gpt-4o"):
                        pass
            else:
                with tracer.start_task(f"task-{i}"):
                    with tracer.start_tool_call(tool_name="search"):
                        pass
    return _time_fn(run)


def bench_span_creation_with_attrs() -> Tuple[float, float]:
    """Create N spans with attributes set on each."""
    def run():
        tracer = AgentTracer(agent_name="bench", framework="benchmark")
        for i in range(N_ITERATIONS):
            kind_idx = i % 3
            if kind_idx == 0:
                with tracer.start_task(f"task-{i}") as span:
                    span.set_attribute("agent.task", f"Summarize document {i}")
                    span.set_attribute("agent.role", "researcher")
            elif kind_idx == 1:
                with tracer.start_task(f"task-{i}"):
                    with tracer.start_llm_call(model="gpt-4o") as span:
                        span.set_attribute("llm.input_tokens", 500 + i)
                        span.set_attribute("llm.output_tokens", 200 + i)
                        span.set_attribute("llm.temperature", 0.7)
            else:
                with tracer.start_task(f"task-{i}"):
                    with tracer.start_tool_call(tool_name="search") as span:
                        span.set_attribute("tool.input", f"query {i}")
                        span.set_attribute("tool.output", f"result {i}")
                        span.set_attribute("tool.success", True)
    return _time_fn(run)


# ---------------------------------------------------------------------------
# 2. Context propagation overhead
# ---------------------------------------------------------------------------
def bench_context_propagation() -> Tuple[float, float]:
    """Round-trip to_carrier / from_carrier for N iterations."""
    def run():
        ctx = AgentContext(
            trace_id="a" * 32,
            parent_span_id="b" * 16,
            source_agent="agent-alpha",
            baggage={"session": "sess-123", "priority": "high"},
        )
        for _ in range(N_ITERATIONS):
            carrier = ctx.to_carrier()
            restored = AgentContext.from_carrier(carrier)
            # Use restored to prevent dead-code elimination
            _ = restored.trace_id
    return _time_fn(run)


# ---------------------------------------------------------------------------
# 3. Exporter overhead
# ---------------------------------------------------------------------------
def _make_sample_span(idx: int) -> AgentSpan:
    """Create a completed sample span for export benchmarks."""
    tracer = AgentTracer(agent_name="bench", framework="benchmark")
    span = tracer._make_span(f"sample-{idx}", AgentSpanKind.LLM_CALL)
    span.set_attribute("llm.model", "gpt-4o")
    span.set_attribute("llm.input_tokens", 500)
    span.set_attribute("llm.output_tokens", 200)
    span.end()
    return span


def bench_console_exporter() -> Tuple[float, float]:
    """Export N spans via ConsoleExporter (stdout redirected to /dev/null)."""
    spans = [_make_sample_span(i) for i in range(N_ITERATIONS)]
    exporter = ConsoleExporter(verbose=False)

    def run():
        old_stdout = sys.stdout
        sys.stdout = DEVNULL
        try:
            for span in spans:
                exporter.export_span(span)
        finally:
            sys.stdout = old_stdout
    return _time_fn(run)


def bench_json_file_exporter() -> Tuple[float, float]:
    """Export N spans via JSONFileExporter to a temp file."""
    spans = [_make_sample_span(i) for i in range(N_ITERATIONS)]

    def run():
        tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            exporter = JSONFileExporter(file_path=tmp_path)
            for span in spans:
                exporter.export_span(span)
        finally:
            os.unlink(tmp_path)
    return _time_fn(run)


# ---------------------------------------------------------------------------
# 4. Memory overhead
# ---------------------------------------------------------------------------
def bench_memory_overhead() -> Tuple[float, float]:
    """Measure memory usage of N accumulated spans (in MB).

    Uses sys.getsizeof with deep traversal for accurate measurement.
    Returns (mean_MB, std_MB) across trials.
    """

    def _deep_sizeof(obj, seen=None) -> int:
        """Recursively compute approximate size of an object graph."""
        if seen is None:
            seen = set()
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        seen.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, dict):
            size += sum(_deep_sizeof(k, seen) + _deep_sizeof(v, seen)
                        for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            size += sum(_deep_sizeof(i, seen) for i in obj)
        elif hasattr(obj, '__dict__'):
            size += _deep_sizeof(obj.__dict__, seen)
        return size

    measurements: List[float] = []
    for _ in range(N_TRIALS):
        gc.collect()
        tracer = AgentTracer(agent_name="bench", framework="benchmark")
        for i in range(N_ITERATIONS):
            with tracer.start_task(f"task-{i}") as span:
                span.set_attribute("llm.model", "gpt-4o")
                span.set_attribute("llm.input_tokens", 500)
                span.set_attribute("llm.output_tokens", 200)
        gc.collect()
        total_bytes = _deep_sizeof(tracer.get_spans())
        delta_mb = total_bytes / (1024 * 1024)
        measurements.append(delta_mb)

    mean = sum(measurements) / len(measurements)
    variance = sum((m - mean) ** 2 for m in measurements) / len(measurements)
    std = math.sqrt(variance)
    return mean, std


# ---------------------------------------------------------------------------
# 5. Nested span overhead
# ---------------------------------------------------------------------------
def bench_nested_spans() -> Tuple[float, float]:
    """Create N deeply nested traces: task -> reasoning -> llm_call -> tool_call."""
    def run():
        tracer = AgentTracer(agent_name="bench", framework="benchmark")
        for i in range(N_NESTED):
            with tracer.start_task(f"task-{i}") as task_span:
                task_span.set_attribute("agent.task", f"Complex analysis {i}")
                with tracer.start_reasoning(f"reasoning-{i}") as reason_span:
                    reason_span.set_attribute("agent.role", "analyst")
                    with tracer.start_llm_call(model="gpt-4o") as llm_span:
                        llm_span.set_attribute("llm.input_tokens", 1000)
                        llm_span.set_attribute("llm.output_tokens", 500)
                        with tracer.start_tool_call(tool_name="code_exec") as tool_span:
                            tool_span.set_attribute("tool.input", "run analysis")
                            tool_span.set_attribute("tool.success", True)
    return _time_fn(run)


# ---------------------------------------------------------------------------
# 6. Cost estimation overhead
# ---------------------------------------------------------------------------
def bench_cost_estimation() -> Tuple[float, float]:
    """Run N cost estimation calculations."""
    models = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-opus-4", "gpt-4-turbo"]

    def run():
        for i in range(N_ITERATIONS):
            model = models[i % len(models)]
            _ = estimate_cost(model, input_tokens=500 + i, output_tokens=200 + i)
    return _time_fn(run)


# ---------------------------------------------------------------------------
# 7. Metrics recording overhead
# ---------------------------------------------------------------------------
def bench_metrics_counter() -> Tuple[float, float]:
    """Increment a counter N times."""
    def run():
        metrics = AgentMetrics(agent_name="bench")
        for i in range(N_ITERATIONS):
            metrics.increment("agent.llm.call.count", 1.0, model="gpt-4o")
    return _time_fn(run)


def bench_metrics_histogram() -> Tuple[float, float]:
    """Record to a histogram N times."""
    def run():
        metrics = AgentMetrics(agent_name="bench")
        for i in range(N_ITERATIONS):
            metrics.record("agent.llm.latency_ms", 150.0 + (i % 100), model="gpt-4o")
    return _time_fn(run)


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------
def _format_time(mean_s: float, std_s: float, n_ops: int) -> str:
    """Format timing result showing total, per-op, and std."""
    per_op_us = (mean_s / n_ops) * 1_000_000  # microseconds
    std_us = (std_s / n_ops) * 1_000_000
    return f"{mean_s*1000:8.1f} ms total | {per_op_us:7.2f} +/- {std_us:5.2f} us/op"


def _format_memory(mean_mb: float, std_mb: float) -> str:
    """Format memory result."""
    return f"{mean_mb:8.2f} +/- {std_mb:5.2f} MB"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 80)
    print("AgentTelemetry Overhead Benchmark")
    print(f"  N_ITERATIONS = {N_ITERATIONS:,}")
    print(f"  N_NESTED     = {N_NESTED:,}")
    print(f"  N_TRIALS     = {N_TRIALS}")
    print(f"  Python       = {sys.version.split()[0]}")
    print(f"  Platform     = {sys.platform}")
    print("=" * 80)
    print()

    # Collect results for summary table
    results: List[Tuple[str, str, float, float, int]] = []

    # 1. Span creation
    print("[1/7] Span creation overhead ...")
    m, s = bench_span_creation_bare()
    print(f"  Bare spans:       {_format_time(m, s, N_ITERATIONS)}")
    results.append(("Span creation (bare)", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    m, s = bench_span_creation_with_attrs()
    print(f"  With attributes:  {_format_time(m, s, N_ITERATIONS)}")
    results.append(("Span creation (w/ attrs)", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    # 2. Context propagation
    print("[2/7] Context propagation overhead ...")
    m, s = bench_context_propagation()
    print(f"  Round-trip:       {_format_time(m, s, N_ITERATIONS)}")
    results.append(("Context propagation", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    # 3. Exporter overhead
    print("[3/7] Exporter overhead ...")
    m, s = bench_console_exporter()
    print(f"  ConsoleExporter:  {_format_time(m, s, N_ITERATIONS)}")
    results.append(("ConsoleExporter", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    m, s = bench_json_file_exporter()
    print(f"  JSONFileExporter: {_format_time(m, s, N_ITERATIONS)}")
    results.append(("JSONFileExporter", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    # 4. Memory overhead
    print("[4/7] Memory overhead ...")
    m, s = bench_memory_overhead()
    print(f"  10k spans:        {_format_memory(m, s)}")
    results.append(("Memory (10k spans)", _format_memory(m, s), m, s, N_ITERATIONS))

    # 5. Nested spans
    print("[5/7] Nested span overhead ...")
    m, s = bench_nested_spans()
    print(f"  Nested traces:    {_format_time(m, s, N_NESTED)}")
    results.append(("Nested spans (4-deep)", _format_time(m, s, N_NESTED), m, s, N_NESTED))

    # 6. Cost estimation
    print("[6/7] Cost estimation overhead ...")
    m, s = bench_cost_estimation()
    print(f"  Cost calc:        {_format_time(m, s, N_ITERATIONS)}")
    results.append(("Cost estimation", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    # 7. Metrics recording
    print("[7/7] Metrics recording overhead ...")
    m, s = bench_metrics_counter()
    print(f"  Counter incr:     {_format_time(m, s, N_ITERATIONS)}")
    results.append(("Counter increment", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    m, s = bench_metrics_histogram()
    print(f"  Histogram record: {_format_time(m, s, N_ITERATIONS)}")
    results.append(("Histogram record", _format_time(m, s, N_ITERATIONS), m, s, N_ITERATIONS))

    # Summary table
    print()
    print("=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    hdr = f"{'Operation':<30} {'Per-op (us)':>15} {'Std (us)':>12} {'Total (ms)':>12}"
    print(hdr)
    print("-" * len(hdr))

    for name, formatted, mean_s, std_s, n_ops in results:
        if name.startswith("Memory"):
            # Memory is special: mean_s is MB not seconds
            print(f"{name:<30} {'---':>15} {'---':>12} {mean_s:>9.2f} MB")
        else:
            per_op_us = (mean_s / n_ops) * 1_000_000
            std_us = (std_s / n_ops) * 1_000_000
            total_ms = mean_s * 1000
            print(f"{name:<30} {per_op_us:>15.2f} {std_us:>12.2f} {total_ms:>12.1f}")

    print("-" * len(hdr))
    print()

    # Context: typical LLM API latency
    print("CONTEXT: Typical LLM API latency = 500,000 - 5,000,000 us (500ms - 5s)")
    # Find the max per-op overhead
    max_per_op = 0.0
    for name, _, mean_s, std_s, n_ops in results:
        if not name.startswith("Memory"):
            per_op_us = (mean_s / n_ops) * 1_000_000
            if per_op_us > max_per_op:
                max_per_op = per_op_us
    if max_per_op > 0:
        overhead_pct = (max_per_op / 500_000) * 100
        print(f"Maximum per-operation overhead: {max_per_op:.2f} us")
        print(f"Overhead vs. minimum LLM call (500ms): {overhead_pct:.4f}%")
        print(f"Overhead vs. typical LLM call (2s):    {(max_per_op / 2_000_000) * 100:.4f}%")
    print()


if __name__ == "__main__":
    main()
