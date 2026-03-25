"""Performance benchmark tests for AgentTelemetry.

Measures instrumentation overhead to verify it stays within acceptable bounds.
"""

import time
import tracemalloc

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agenttelemetry.core.spans import (
    AgentSpanKind,
    AGENT_SPAN_KIND,
    LLM_MODEL,
    LLM_INPUT_TOKENS,
    LLM_OUTPUT_TOKENS,
    start_agent_span,
)


@pytest.fixture()
def bench_provider():
    """Provider with in-memory exporter for benchmarks."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield provider, exporter
    provider.shutdown()


class TestSpanCreationOverhead:
    """Measure time overhead of span creation."""

    def test_single_span_under_5ms(self, bench_provider):
        provider, exporter = bench_provider
        tracer = provider.get_tracer("bench")

        # Warm up
        with start_agent_span("warmup", AgentSpanKind.LLM_CALL, tracer=tracer):
            pass
        exporter.clear()

        # Measure
        iterations = 100
        start = time.perf_counter()
        for i in range(iterations):
            with start_agent_span(
                f"span-{i}",
                AgentSpanKind.LLM_CALL,
                tracer=tracer,
                attributes={
                    LLM_MODEL: "gpt-4o",
                    LLM_INPUT_TOKENS: 100,
                    LLM_OUTPUT_TOKENS: 50,
                },
            ):
                pass
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        assert avg_ms < 5.0, f"Average span creation took {avg_ms:.2f}ms (limit: 5ms)"

    def test_nested_spans_under_10ms(self, bench_provider):
        provider, exporter = bench_provider
        tracer = provider.get_tracer("bench")

        # Warm up
        with start_agent_span("warmup", AgentSpanKind.AGENT, tracer=tracer):
            with start_agent_span("warmup-child", AgentSpanKind.LLM_CALL, tracer=tracer):
                pass
        exporter.clear()

        # Measure nested span creation (agent -> llm_call -> tool_call)
        iterations = 50
        start = time.perf_counter()
        for i in range(iterations):
            with start_agent_span(f"agent-{i}", AgentSpanKind.AGENT, tracer=tracer):
                with start_agent_span(f"llm-{i}", AgentSpanKind.LLM_CALL, tracer=tracer):
                    with start_agent_span(f"tool-{i}", AgentSpanKind.TOOL_CALL, tracer=tracer):
                        pass
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        assert avg_ms < 10.0, f"Average nested span set took {avg_ms:.2f}ms (limit: 10ms)"

    def test_uninstrumented_baseline(self):
        """Baseline: function call without any instrumentation."""
        def bare_function():
            _ = {"model": "gpt-4o", "tokens": 100}

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            bare_function()
        elapsed = time.perf_counter() - start

        avg_us = (elapsed / iterations) * 1_000_000
        # Just record the baseline — not an assertion
        assert avg_us < 1000, f"Bare function took {avg_us:.1f}us (sanity check)"


class TestMemoryOverhead:
    """Measure memory overhead of span creation."""

    def test_span_memory_overhead(self, bench_provider):
        provider, exporter = bench_provider
        tracer = provider.get_tracer("bench")

        # Measure memory for creating many spans
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        num_spans = 1000
        for i in range(num_spans):
            with start_agent_span(
                f"span-{i}",
                AgentSpanKind.LLM_CALL,
                tracer=tracer,
                attributes={
                    LLM_MODEL: "gpt-4o",
                    LLM_INPUT_TOKENS: 100,
                    LLM_OUTPUT_TOKENS: 50,
                },
            ):
                pass

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Calculate memory difference
        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_increase = sum(s.size_diff for s in stats if s.size_diff > 0)
        per_span_bytes = total_increase / num_spans

        # Each span should use less than 10KB
        assert per_span_bytes < 10_000, (
            f"Per-span memory: {per_span_bytes:.0f} bytes (limit: 10,000)"
        )

    def test_exporter_retains_spans(self, bench_provider):
        provider, exporter = bench_provider
        tracer = provider.get_tracer("bench")

        num_spans = 100
        for i in range(num_spans):
            with start_agent_span(f"span-{i}", AgentSpanKind.LLM_CALL, tracer=tracer):
                pass

        finished = exporter.get_finished_spans()
        assert len(finished) == num_spans


class TestThroughput:
    """Measure span creation throughput."""

    def test_can_create_1000_spans_per_second(self, bench_provider):
        provider, exporter = bench_provider
        tracer = provider.get_tracer("bench")

        # Warm up
        with start_agent_span("warmup", AgentSpanKind.LLM_CALL, tracer=tracer):
            pass
        exporter.clear()

        num_spans = 1000
        start = time.perf_counter()
        for i in range(num_spans):
            with start_agent_span(f"span-{i}", AgentSpanKind.LLM_CALL, tracer=tracer):
                pass
        elapsed = time.perf_counter() - start

        throughput = num_spans / elapsed
        assert throughput > 1000, (
            f"Throughput: {throughput:.0f} spans/sec (minimum: 1000)"
        )
