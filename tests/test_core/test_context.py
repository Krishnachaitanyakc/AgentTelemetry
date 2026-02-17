"""Comprehensive tests for AgentContext."""

import pytest

from agenttelemetry.core.context import (
    AgentContext,
    TRACEPARENT_KEY,
    AGENTSTATE_KEY,
)
from agenttelemetry.core.trace import AgentTracer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_context():
    """A simple AgentContext for testing."""
    return AgentContext(
        trace_id="abcdef1234567890abcdef1234567890",
        parent_span_id="1234567890abcdef",
        source_agent="agent-a",
    )


@pytest.fixture
def context_with_baggage():
    """An AgentContext with baggage items."""
    return AgentContext(
        trace_id="aabbccdd11223344aabbccdd11223344",
        parent_span_id="deadbeefcafebabe",
        source_agent="agent-b",
        baggage={"session_id": "sess-001", "user_id": "u-42"},
    )


# ===================================================================
# Construction tests
# ===================================================================


class TestConstruction:
    """Tests for AgentContext construction."""

    def test_basic_fields(self, sample_context):
        assert sample_context.trace_id == "abcdef1234567890abcdef1234567890"
        assert sample_context.parent_span_id == "1234567890abcdef"
        assert sample_context.source_agent == "agent-a"

    def test_default_baggage_is_empty_dict(self):
        ctx = AgentContext(trace_id="t", parent_span_id="s")
        assert ctx.baggage == {}

    def test_default_source_agent_is_empty(self):
        ctx = AgentContext(trace_id="t", parent_span_id="s")
        assert ctx.source_agent == ""

    def test_none_baggage_becomes_empty_dict(self):
        ctx = AgentContext(trace_id="t", parent_span_id="s", baggage=None)
        assert ctx.baggage == {}

    def test_baggage_stored(self, context_with_baggage):
        assert context_with_baggage.baggage == {
            "session_id": "sess-001",
            "user_id": "u-42",
        }

    def test_separate_instances_have_separate_baggage(self):
        """Ensure __post_init__ does not share a mutable default across instances."""
        ctx1 = AgentContext(trace_id="t1", parent_span_id="s1")
        ctx2 = AgentContext(trace_id="t2", parent_span_id="s2")
        ctx1.baggage["key"] = "val"
        assert "key" not in ctx2.baggage


# ===================================================================
# Serialization (to_carrier) tests
# ===================================================================


class TestToCarrier:
    """Tests for serializing context to a carrier dict."""

    def test_traceparent_format(self, sample_context):
        carrier = sample_context.to_carrier()
        expected = "00-abcdef1234567890abcdef1234567890-1234567890abcdef-01"
        assert carrier[TRACEPARENT_KEY] == expected

    def test_agentstate_is_source_agent(self, sample_context):
        carrier = sample_context.to_carrier()
        assert carrier[AGENTSTATE_KEY] == "agent-a"

    def test_no_baggage_key_when_baggage_empty(self, sample_context):
        carrier = sample_context.to_carrier()
        assert "baggage" not in carrier

    def test_baggage_serialized(self, context_with_baggage):
        carrier = context_with_baggage.to_carrier()
        assert "baggage" in carrier
        # Baggage should contain both key=value pairs separated by commas
        baggage_str = carrier["baggage"]
        assert "session_id=sess-001" in baggage_str
        assert "user_id=u-42" in baggage_str

    def test_carrier_keys(self, sample_context):
        carrier = sample_context.to_carrier()
        assert TRACEPARENT_KEY in carrier
        assert AGENTSTATE_KEY in carrier

    def test_empty_source_agent(self):
        ctx = AgentContext(trace_id="t", parent_span_id="s", source_agent="")
        carrier = ctx.to_carrier()
        assert carrier[AGENTSTATE_KEY] == ""


# ===================================================================
# Deserialization (from_carrier) tests
# ===================================================================


class TestFromCarrier:
    """Tests for deserializing context from a carrier dict."""

    def test_basic_deserialization(self):
        carrier = {
            TRACEPARENT_KEY: "00-trace1234-span5678-01",
            AGENTSTATE_KEY: "agent-x",
        }
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.trace_id == "trace1234"
        assert ctx.parent_span_id == "span5678"
        assert ctx.source_agent == "agent-x"

    def test_missing_traceparent(self):
        carrier = {AGENTSTATE_KEY: "agent-x"}
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.trace_id == ""
        assert ctx.parent_span_id == ""

    def test_missing_agentstate(self):
        carrier = {TRACEPARENT_KEY: "00-t-s-01"}
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.source_agent == ""

    def test_empty_carrier(self):
        ctx = AgentContext.from_carrier({})
        assert ctx.trace_id == ""
        assert ctx.parent_span_id == ""
        assert ctx.source_agent == ""
        assert ctx.baggage == {}

    def test_malformed_traceparent_too_few_parts(self):
        carrier = {TRACEPARENT_KEY: "invalid"}
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.trace_id == ""
        assert ctx.parent_span_id == ""

    def test_traceparent_with_extra_parts(self):
        carrier = {TRACEPARENT_KEY: "00-trace-span-01-extra-parts"}
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.trace_id == "trace"
        assert ctx.parent_span_id == "span"

    def test_baggage_deserialization(self):
        carrier = {
            TRACEPARENT_KEY: "00-t-s-01",
            "baggage": "key1=val1,key2=val2",
        }
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.baggage == {"key1": "val1", "key2": "val2"}

    def test_baggage_with_spaces(self):
        carrier = {
            TRACEPARENT_KEY: "00-t-s-01",
            "baggage": " key1 = val1 , key2 = val2 ",
        }
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.baggage == {"key1": "val1", "key2": "val2"}

    def test_empty_baggage_string(self):
        carrier = {
            TRACEPARENT_KEY: "00-t-s-01",
            "baggage": "",
        }
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.baggage == {}

    def test_baggage_with_equals_in_value(self):
        """Baggage values may contain '=' characters."""
        carrier = {
            TRACEPARENT_KEY: "00-t-s-01",
            "baggage": "key=val=with=equals",
        }
        ctx = AgentContext.from_carrier(carrier)
        assert ctx.baggage == {"key": "val=with=equals"}

    def test_baggage_item_without_equals_is_skipped(self):
        carrier = {
            TRACEPARENT_KEY: "00-t-s-01",
            "baggage": "good=yes,badentry,also_good=yes",
        }
        ctx = AgentContext.from_carrier(carrier)
        assert "good" in ctx.baggage
        assert "also_good" in ctx.baggage
        assert "badentry" not in ctx.baggage


# ===================================================================
# Round-trip preservation tests
# ===================================================================


class TestRoundTrip:
    """Tests that to_carrier -> from_carrier preserves all data."""

    def test_round_trip_basic(self, sample_context):
        carrier = sample_context.to_carrier()
        restored = AgentContext.from_carrier(carrier)
        assert restored.trace_id == sample_context.trace_id
        assert restored.parent_span_id == sample_context.parent_span_id
        assert restored.source_agent == sample_context.source_agent

    def test_round_trip_with_baggage(self, context_with_baggage):
        carrier = context_with_baggage.to_carrier()
        restored = AgentContext.from_carrier(carrier)
        assert restored.trace_id == context_with_baggage.trace_id
        assert restored.parent_span_id == context_with_baggage.parent_span_id
        assert restored.source_agent == context_with_baggage.source_agent
        assert restored.baggage == context_with_baggage.baggage

    def test_round_trip_empty_baggage(self):
        ctx = AgentContext(trace_id="t123", parent_span_id="s456", source_agent="a")
        carrier = ctx.to_carrier()
        restored = AgentContext.from_carrier(carrier)
        assert restored.baggage == {}

    def test_double_round_trip(self, context_with_baggage):
        """Serialize -> deserialize -> serialize -> deserialize should be stable."""
        carrier1 = context_with_baggage.to_carrier()
        ctx1 = AgentContext.from_carrier(carrier1)
        carrier2 = ctx1.to_carrier()
        ctx2 = AgentContext.from_carrier(carrier2)
        assert ctx2.trace_id == context_with_baggage.trace_id
        assert ctx2.parent_span_id == context_with_baggage.parent_span_id
        assert ctx2.source_agent == context_with_baggage.source_agent
        assert ctx2.baggage == context_with_baggage.baggage

    def test_round_trip_preserves_many_baggage_items(self):
        baggage = {f"key{i}": f"value{i}" for i in range(20)}
        ctx = AgentContext(
            trace_id="t",
            parent_span_id="s",
            source_agent="a",
            baggage=baggage,
        )
        restored = AgentContext.from_carrier(ctx.to_carrier())
        assert restored.baggage == baggage


# ===================================================================
# Baggage propagation tests
# ===================================================================


class TestBaggagePropagation:
    """Tests specifically focused on baggage handling."""

    def test_baggage_mutation_does_not_affect_original(self):
        ctx = AgentContext(
            trace_id="t", parent_span_id="s", baggage={"a": "1"}
        )
        carrier = ctx.to_carrier()
        restored = AgentContext.from_carrier(carrier)
        restored.baggage["b"] = "2"
        assert "b" not in ctx.baggage

    def test_single_baggage_item(self):
        ctx = AgentContext(
            trace_id="t", parent_span_id="s", baggage={"only": "one"}
        )
        carrier = ctx.to_carrier()
        assert carrier["baggage"] == "only=one"
        restored = AgentContext.from_carrier(carrier)
        assert restored.baggage == {"only": "one"}

    def test_baggage_with_numeric_values(self):
        ctx = AgentContext(
            trace_id="t",
            parent_span_id="s",
            baggage={"count": "42", "pi": "3.14"},
        )
        carrier = ctx.to_carrier()
        restored = AgentContext.from_carrier(carrier)
        assert restored.baggage["count"] == "42"
        assert restored.baggage["pi"] == "3.14"


# ===================================================================
# from_tracer tests
# ===================================================================


class TestFromTracer:
    """Tests for creating context from an active tracer."""

    def test_from_tracer_with_active_span(self):
        tracer = AgentTracer(agent_name="agent-a")
        with tracer.start_task("work") as span:
            ctx = AgentContext.from_tracer(tracer)
            assert ctx is not None
            assert ctx.trace_id == span.trace_id
            assert ctx.parent_span_id == span.span_id
            assert ctx.source_agent == "agent-a"

    def test_from_tracer_with_no_active_span(self):
        tracer = AgentTracer(agent_name="idle")
        ctx = AgentContext.from_tracer(tracer)
        assert ctx is None

    def test_from_tracer_uses_deepest_active_span(self):
        tracer = AgentTracer(agent_name="nested")
        with tracer.start_task("root") as root:
            with tracer.start_llm_call("m") as child:
                ctx = AgentContext.from_tracer(tracer)
                # Should use the deepest (most recent) active span
                assert ctx.parent_span_id == child.span_id
                assert ctx.trace_id == root.trace_id

    def test_from_tracer_context_round_trip(self):
        """Extract context from tracer, serialize, deserialize, and verify."""
        tracer = AgentTracer(agent_name="source")
        with tracer.start_task("job") as span:
            ctx = AgentContext.from_tracer(tracer)
            carrier = ctx.to_carrier()
            restored = AgentContext.from_carrier(carrier)
            assert restored.trace_id == span.trace_id
            assert restored.parent_span_id == span.span_id
            assert restored.source_agent == "source"


# ===================================================================
# Cross-agent propagation scenario tests
# ===================================================================


class TestCrossAgentPropagation:
    """End-to-end tests simulating multi-agent context propagation."""

    def test_two_agent_trace_continuity(self):
        """Agent A creates context, Agent B receives it and continues the trace."""
        tracer_a = AgentTracer(agent_name="agent-a")
        tracer_b = AgentTracer(agent_name="agent-b")

        with tracer_a.start_task("plan") as span_a:
            ctx = AgentContext.from_tracer(tracer_a)
            carrier = ctx.to_carrier()

        # Agent B deserializes the context
        ctx_b = AgentContext.from_carrier(carrier)
        assert ctx_b.trace_id == span_a.trace_id
        assert ctx_b.parent_span_id == span_a.span_id
        assert ctx_b.source_agent == "agent-a"
