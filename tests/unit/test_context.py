"""Unit tests for agenttelemetry.core.context."""

import pytest
from opentelemetry import trace, context, baggage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agenttelemetry.core.context import (
    AgentContextPropagator,
    AGENT_ID_KEY,
    PARENT_AGENT_ID_KEY,
)


class TestAgentContextPropagator:
    """Tests for context propagation across agent boundaries."""

    def setup_method(self):
        self.propagator = AgentContextPropagator()

    def test_inject_adds_traceparent_header(self, fresh_tracer_provider, tracer):
        with tracer.start_as_current_span("test"):
            carrier = {}
            self.propagator.inject_context(carrier)
            assert "traceparent" in carrier
            # W3C traceparent format: version-trace_id-span_id-flags
            parts = carrier["traceparent"].split("-")
            assert len(parts) == 4
            assert parts[0] == "00"  # version

    def test_extract_restores_context(self, fresh_tracer_provider, tracer):
        with tracer.start_as_current_span("original"):
            carrier = {}
            self.propagator.inject_context(carrier)

        # Extract into a new context
        restored_ctx = self.propagator.extract_context(carrier)
        span_ctx = trace.get_current_span(restored_ctx).get_span_context()
        assert span_ctx.trace_id != 0

    def test_round_trip_preserves_trace_id(self, fresh_tracer_provider, tracer):
        with tracer.start_as_current_span("span-a") as span_a:
            original_trace_id = span_a.get_span_context().trace_id
            carrier = {}
            self.propagator.inject_context(carrier)

        restored_ctx = self.propagator.extract_context(carrier)
        restored_span_ctx = trace.get_current_span(restored_ctx).get_span_context()
        assert restored_span_ctx.trace_id == original_trace_id

    def test_inject_agent_id_in_baggage(self, fresh_tracer_provider, tracer):
        with tracer.start_as_current_span("test"):
            carrier = {}
            self.propagator.inject_context(carrier, agent_id="agent-001")
            assert "baggage" in carrier
            assert "agent_id" in carrier["baggage"]

    def test_extract_agent_id_from_baggage(self, fresh_tracer_provider, tracer):
        with tracer.start_as_current_span("test"):
            carrier = {}
            self.propagator.inject_context(carrier, agent_id="agent-001")

        restored_ctx = self.propagator.extract_context(carrier)
        agent_id = AgentContextPropagator.get_agent_id(restored_ctx)
        assert agent_id == "agent-001"

    def test_inject_parent_agent_id_in_baggage(self, fresh_tracer_provider, tracer):
        with tracer.start_as_current_span("test"):
            carrier = {}
            self.propagator.inject_context(
                carrier, agent_id="child-agent", parent_agent_id="parent-agent"
            )

        restored_ctx = self.propagator.extract_context(carrier)
        parent_id = AgentContextPropagator.get_parent_agent_id(restored_ctx)
        assert parent_id == "parent-agent"

    def test_set_and_get_agent_id(self):
        ctx = AgentContextPropagator.set_agent_id("my-agent")
        retrieved = AgentContextPropagator.get_agent_id(ctx)
        assert retrieved == "my-agent"

    def test_set_and_get_parent_agent_id(self):
        ctx = AgentContextPropagator.set_parent_agent_id("parent-42")
        retrieved = AgentContextPropagator.get_parent_agent_id(ctx)
        assert retrieved == "parent-42"

    def test_get_agent_id_returns_none_when_not_set(self):
        # Use a fresh empty context
        ctx = context.Context()
        retrieved = AgentContextPropagator.get_agent_id(ctx)
        assert retrieved is None

    def test_get_parent_agent_id_returns_none_when_not_set(self):
        ctx = context.Context()
        retrieved = AgentContextPropagator.get_parent_agent_id(ctx)
        assert retrieved is None

    def test_round_trip_with_both_ids(self, fresh_tracer_provider, tracer):
        with tracer.start_as_current_span("delegating-span"):
            carrier = {}
            self.propagator.inject_context(
                carrier,
                agent_id="worker-agent",
                parent_agent_id="orchestrator",
            )

        restored_ctx = self.propagator.extract_context(carrier)
        assert AgentContextPropagator.get_agent_id(restored_ctx) == "worker-agent"
        assert AgentContextPropagator.get_parent_agent_id(restored_ctx) == "orchestrator"
