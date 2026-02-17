"""Comprehensive tests for AgentTracer and AgentSpan."""

import time
import uuid

import pytest

from agenttelemetry.core.trace import (
    AgentSpan,
    AgentSpanKind,
    AgentTracer,
    SpanStatus,
    estimate_cost,
    ATTR_AGENT_NAME,
    ATTR_AGENT_FRAMEWORK,
    ATTR_AGENT_FRAMEWORK_VERSION,
    ATTR_LLM_MODEL,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_COST_USD,
    ATTR_TOOL_NAME,
    ATTR_TOOL_SUCCESS,
    ATTR_TOOL_ERROR,
    ATTR_INTERACTION_SOURCE,
    ATTR_INTERACTION_TARGET,
)
from agenttelemetry.core.events import EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tracer():
    """Return a fresh AgentTracer with default settings."""
    return AgentTracer(agent_name="test-agent", framework="pytest")


@pytest.fixture
def tracer_with_version():
    """Tracer that has framework_version set."""
    return AgentTracer(
        agent_name="versioned-agent",
        framework="pytest",
        framework_version="7.4.0",
    )


# ===================================================================
# AgentSpan unit tests
# ===================================================================


class TestAgentSpan:
    """Tests for the AgentSpan dataclass directly."""

    def _make_span(self, **overrides):
        defaults = dict(
            trace_id="abc123",
            span_id="def456",
            parent_span_id=None,
            name="test-span",
            kind=AgentSpanKind.TASK,
            start_time_ns=time.time_ns(),
        )
        defaults.update(overrides)
        return AgentSpan(**defaults)

    # -- ID fields --

    def test_span_stores_trace_id_and_span_id(self):
        span = self._make_span(trace_id="t1", span_id="s1")
        assert span.trace_id == "t1"
        assert span.span_id == "s1"

    def test_span_stores_parent_span_id(self):
        span = self._make_span(parent_span_id="parent1")
        assert span.parent_span_id == "parent1"

    def test_span_parent_span_id_defaults_to_none(self):
        span = self._make_span()
        assert span.parent_span_id is None

    # -- Kind --

    def test_span_kind(self):
        for kind in AgentSpanKind:
            span = self._make_span(kind=kind)
            assert span.kind is kind

    # -- Status --

    def test_default_status_is_unset(self):
        span = self._make_span()
        assert span.status is SpanStatus.UNSET

    def test_set_status_ok(self):
        span = self._make_span()
        span.set_status(SpanStatus.OK)
        assert span.status is SpanStatus.OK

    def test_set_status_error_with_description(self):
        span = self._make_span()
        span.set_status(SpanStatus.ERROR, "something failed")
        assert span.status is SpanStatus.ERROR
        assert span.attributes["status.description"] == "something failed"

    def test_set_status_without_description_does_not_add_key(self):
        span = self._make_span()
        span.set_status(SpanStatus.TIMEOUT)
        assert span.status is SpanStatus.TIMEOUT
        assert "status.description" not in span.attributes

    # -- Duration --

    def test_duration_is_zero_before_end(self):
        span = self._make_span()
        assert span.duration_ms == 0.0

    def test_duration_calculated_after_end(self):
        start = time.time_ns()
        span = self._make_span(start_time_ns=start)
        # Simulate a 10ms duration
        span.end_time_ns = start + 10_000_000  # 10ms in ns
        assert span.duration_ms == pytest.approx(10.0)

    def test_end_sets_end_time_ns(self):
        span = self._make_span()
        assert span.end_time_ns == 0
        span.end()
        assert span.end_time_ns > 0

    def test_end_promotes_unset_to_ok(self):
        span = self._make_span()
        assert span.status is SpanStatus.UNSET
        span.end()
        assert span.status is SpanStatus.OK

    def test_end_preserves_error_status(self):
        span = self._make_span()
        span.set_status(SpanStatus.ERROR, "broke")
        span.end()
        assert span.status is SpanStatus.ERROR

    # -- Attributes --

    def test_set_attribute(self):
        span = self._make_span()
        span.set_attribute("foo", "bar")
        assert span.attributes["foo"] == "bar"

    def test_set_attribute_overwrites(self):
        span = self._make_span()
        span.set_attribute("key", 1)
        span.set_attribute("key", 2)
        assert span.attributes["key"] == 2

    # -- Convenience accessors --

    def test_agent_name_accessor(self):
        span = self._make_span()
        span.set_attribute(ATTR_AGENT_NAME, "my-agent")
        assert span.agent_name == "my-agent"

    def test_agent_name_returns_none_when_missing(self):
        span = self._make_span()
        assert span.agent_name is None

    def test_model_accessor(self):
        span = self._make_span()
        span.set_attribute(ATTR_LLM_MODEL, "gpt-4o")
        assert span.model == "gpt-4o"

    def test_input_tokens_default(self):
        span = self._make_span()
        assert span.input_tokens == 0

    def test_output_tokens_default(self):
        span = self._make_span()
        assert span.output_tokens == 0

    def test_cost_usd_default(self):
        span = self._make_span()
        assert span.cost_usd == 0.0

    def test_tool_name_accessor(self):
        span = self._make_span()
        span.set_attribute(ATTR_TOOL_NAME, "search")
        assert span.tool_name == "search"

    # -- Events --

    def test_add_event(self):
        span = self._make_span()
        span.add_event("my_event", EventType.CUSTOM, detail="hello")
        assert len(span.events) == 1
        event = span.events[0]
        assert event.name == "my_event"
        assert event.event_type is EventType.CUSTOM
        assert event.attributes["detail"] == "hello"
        assert event.timestamp_ns > 0

    def test_add_multiple_events(self):
        span = self._make_span()
        span.add_event("e1", EventType.LLM_START)
        span.add_event("e2", EventType.LLM_END)
        assert len(span.events) == 2

    # -- Serialization --

    def test_to_dict_has_required_keys(self):
        span = self._make_span(trace_id="t1", span_id="s1", name="op")
        span.end()
        d = span.to_dict()
        assert d["trace_id"] == "t1"
        assert d["span_id"] == "s1"
        assert d["name"] == "op"
        assert d["kind"] == "task"
        assert d["status"] == "ok"
        assert "start_time_ns" in d
        assert "end_time_ns" in d
        assert "duration_ms" in d
        assert "attributes" in d
        assert "events" in d

    def test_to_dict_includes_events(self):
        span = self._make_span()
        span.add_event("test", EventType.ERROR, msg="oops")
        span.end()
        d = span.to_dict()
        assert len(d["events"]) == 1
        assert d["events"][0]["event_type"] == "error"
        assert d["events"][0]["attributes"]["msg"] == "oops"

    def test_to_dict_parent_span_id_none(self):
        span = self._make_span(parent_span_id=None)
        d = span.to_dict()
        assert d["parent_span_id"] is None

    def test_to_dict_parent_span_id_present(self):
        span = self._make_span(parent_span_id="p123")
        d = span.to_dict()
        assert d["parent_span_id"] == "p123"


# ===================================================================
# Cost estimation tests
# ===================================================================


class TestEstimateCost:
    """Tests for the estimate_cost function."""

    def test_known_model_gpt4o(self):
        # gpt-4o: input=2.50/1M, output=10.00/1M
        cost = estimate_cost("gpt-4o", input_tokens=1_000_000, output_tokens=0)
        assert cost == pytest.approx(2.50)

    def test_known_model_gpt4o_output(self):
        cost = estimate_cost("gpt-4o", input_tokens=0, output_tokens=1_000_000)
        assert cost == pytest.approx(10.00)

    def test_known_model_mixed_tokens(self):
        # 500 input + 200 output for gpt-4o
        cost = estimate_cost("gpt-4o", input_tokens=500, output_tokens=200)
        expected = 500 * 2.50 / 1_000_000 + 200 * 10.00 / 1_000_000
        assert cost == pytest.approx(expected)

    def test_known_model_claude_opus(self):
        cost = estimate_cost("claude-3-opus", input_tokens=1000, output_tokens=500)
        expected = 1000 * 15.00 / 1_000_000 + 500 * 75.00 / 1_000_000
        assert cost == pytest.approx(expected)

    def test_known_model_claude_sonnet_4(self):
        cost = estimate_cost("claude-sonnet-4", input_tokens=1000, output_tokens=1000)
        expected = 1000 * 3.00 / 1_000_000 + 1000 * 15.00 / 1_000_000
        assert cost == pytest.approx(expected)

    def test_case_insensitive_matching(self):
        cost = estimate_cost("GPT-4o", input_tokens=1000, output_tokens=0)
        assert cost > 0

    def test_model_as_substring(self):
        # "gpt-4o" should match "openai/gpt-4o-2024-05-13"
        cost = estimate_cost("openai/gpt-4o-2024-05-13", input_tokens=1000, output_tokens=0)
        # Should match gpt-4o-mini or gpt-4o (whichever comes first in iteration)
        assert cost > 0

    def test_unknown_model_returns_zero(self):
        cost = estimate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=500)
        assert cost == 0.0

    def test_zero_tokens(self):
        cost = estimate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_whitespace_stripped(self):
        cost = estimate_cost("  gpt-4o  ", input_tokens=1000, output_tokens=0)
        assert cost > 0


# ===================================================================
# AgentTracer tests
# ===================================================================


class TestAgentTracer:
    """Tests for AgentTracer."""

    # -- Construction --

    def test_tracer_stores_agent_name(self, tracer):
        assert tracer.agent_name == "test-agent"

    def test_tracer_capture_content_default_false(self, tracer):
        assert tracer.capture_content is False

    def test_tracer_capture_content_enabled(self):
        t = AgentTracer(agent_name="a", capture_content=True)
        assert t.capture_content is True

    def test_tracer_starts_with_no_spans(self, tracer):
        assert tracer.get_spans() == []

    # -- Task spans --

    def test_start_task_creates_span(self, tracer):
        with tracer.start_task("do stuff") as span:
            assert span.name == "do stuff"
            assert span.kind is AgentSpanKind.TASK
        assert len(tracer.get_spans()) == 1

    def test_task_span_has_unique_trace_id(self, tracer):
        with tracer.start_task("t1") as s1:
            trace_id = s1.trace_id
        assert len(trace_id) == 32
        # Start a second task; should get a different trace_id
        with tracer.start_task("t2") as s2:
            pass
        assert s1.trace_id != s2.trace_id

    def test_task_span_has_unique_span_id(self, tracer):
        with tracer.start_task("t1") as s1:
            pass
        with tracer.start_task("t2") as s2:
            pass
        assert s1.span_id != s2.span_id

    def test_task_span_root_has_no_parent(self, tracer):
        with tracer.start_task("root") as span:
            assert span.parent_span_id is None

    def test_task_span_gets_agent_attributes(self, tracer):
        with tracer.start_task("job") as span:
            pass
        assert span.attributes[ATTR_AGENT_NAME] == "test-agent"
        assert span.attributes[ATTR_AGENT_FRAMEWORK] == "pytest"

    def test_task_span_gets_framework_version(self, tracer_with_version):
        with tracer_with_version.start_task("job") as span:
            pass
        assert span.attributes[ATTR_AGENT_FRAMEWORK_VERSION] == "7.4.0"

    def test_task_span_no_framework_version_when_empty(self, tracer):
        with tracer.start_task("job") as span:
            pass
        assert ATTR_AGENT_FRAMEWORK_VERSION not in span.attributes

    def test_task_span_custom_attrs(self, tracer):
        with tracer.start_task("job", **{"custom.key": "val"}) as span:
            pass
        assert span.attributes["custom.key"] == "val"

    def test_task_span_status_ok_on_success(self, tracer):
        with tracer.start_task("ok"):
            pass
        span = tracer.get_spans()[0]
        assert span.status is SpanStatus.OK

    def test_task_span_has_positive_duration(self, tracer):
        with tracer.start_task("work") as span:
            # Ensure some measurable time elapses
            time.sleep(0.001)
        assert span.duration_ms > 0

    # -- Parent-child relationships --

    def test_child_span_inherits_trace_id(self, tracer):
        with tracer.start_task("parent") as parent:
            with tracer.start_llm_call(model="gpt-4o") as child:
                pass
        assert child.trace_id == parent.trace_id

    def test_child_span_parent_id_matches_parent_span_id(self, tracer):
        with tracer.start_task("parent") as parent:
            with tracer.start_llm_call(model="gpt-4o") as child:
                pass
        assert child.parent_span_id == parent.span_id

    def test_nested_children_form_chain(self, tracer):
        with tracer.start_task("root") as root:
            with tracer.start_reasoning("think") as r_span:
                with tracer.start_llm_call("gpt-4o") as llm_span:
                    pass
        assert root.parent_span_id is None
        assert r_span.parent_span_id == root.span_id
        assert llm_span.parent_span_id == r_span.span_id
        # All share the same trace_id
        assert root.trace_id == r_span.trace_id == llm_span.trace_id

    def test_sibling_spans_share_parent(self, tracer):
        with tracer.start_task("root") as root:
            with tracer.start_llm_call("m1") as s1:
                pass
            with tracer.start_tool_call("t1") as s2:
                pass
        assert s1.parent_span_id == root.span_id
        assert s2.parent_span_id == root.span_id
        assert s1.span_id != s2.span_id

    # -- LLM call spans --

    def test_llm_call_span_kind(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_llm_call("gpt-4o") as span:
                pass
        assert span.kind is AgentSpanKind.LLM_CALL

    def test_llm_call_span_name_includes_model(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_llm_call("gpt-4o") as span:
                pass
        assert span.name == "llm.gpt-4o"

    def test_llm_call_sets_model_attribute(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_llm_call("claude-3-opus") as span:
                pass
        assert span.model == "claude-3-opus"

    def test_llm_call_auto_cost_estimation(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_llm_call("gpt-4o") as span:
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, 1000)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 500)
        # Cost should be auto-calculated upon finish
        expected = 1000 * 2.50 / 1_000_000 + 500 * 10.00 / 1_000_000
        assert span.cost_usd == pytest.approx(expected)

    def test_llm_call_no_cost_for_unknown_model(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_llm_call("unknown-model") as span:
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, 1000)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 500)
        assert span.cost_usd == 0.0

    def test_llm_call_cost_not_set_when_zero_tokens(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_llm_call("gpt-4o") as span:
                pass
        # No tokens set, cost should remain default
        assert span.cost_usd == 0.0

    # -- Tool call spans --

    def test_tool_call_span_kind(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_tool_call("search") as span:
                pass
        assert span.kind is AgentSpanKind.TOOL_CALL

    def test_tool_call_span_name_includes_tool(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_tool_call("web_search") as span:
                pass
        assert span.name == "tool.web_search"

    def test_tool_call_sets_tool_name(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_tool_call("calculator") as span:
                pass
        assert span.tool_name == "calculator"

    def test_tool_call_auto_success_true(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_tool_call("cmd") as span:
                pass
        assert span.attributes[ATTR_TOOL_SUCCESS] is True

    def test_tool_call_error_sets_success_false(self, tracer):
        with pytest.raises(ValueError):
            with tracer.start_task("root"):
                with tracer.start_tool_call("bad_tool") as span:
                    raise ValueError("tool broke")
        assert span.attributes[ATTR_TOOL_SUCCESS] is False
        assert span.attributes[ATTR_TOOL_ERROR] == "tool broke"
        assert span.status is SpanStatus.ERROR

    # -- Reasoning, planning, retrieval spans --

    def test_reasoning_span_kind(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_reasoning("think") as span:
                pass
        assert span.kind is AgentSpanKind.REASONING

    def test_planning_span_kind(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_planning("plan") as span:
                pass
        assert span.kind is AgentSpanKind.PLANNING

    def test_retrieval_span_kind(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_retrieval("fetch") as span:
                pass
        assert span.kind is AgentSpanKind.RETRIEVAL

    # -- Agent communication spans --

    def test_agent_comm_span_kind(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_agent_comm("other-agent") as span:
                pass
        assert span.kind is AgentSpanKind.AGENT_COMM

    def test_agent_comm_sets_source_and_target(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_agent_comm("other-agent") as span:
                pass
        assert span.attributes[ATTR_INTERACTION_SOURCE] == "test-agent"
        assert span.attributes[ATTR_INTERACTION_TARGET] == "other-agent"

    def test_agent_comm_name(self, tracer):
        with tracer.start_task("root"):
            with tracer.start_agent_comm("b") as span:
                pass
        assert span.name == "comm.test-agent->b"

    # -- Error handling --

    def test_exception_sets_error_status_on_task(self, tracer):
        with pytest.raises(RuntimeError):
            with tracer.start_task("fail") as span:
                raise RuntimeError("boom")
        assert span.status is SpanStatus.ERROR
        assert span.attributes["status.description"] == "boom"

    def test_exception_adds_error_event_on_task(self, tracer):
        with pytest.raises(RuntimeError):
            with tracer.start_task("fail") as span:
                raise RuntimeError("boom")
        assert len(span.events) == 1
        assert span.events[0].event_type is EventType.ERROR
        assert span.events[0].attributes["error"] == "boom"

    def test_exception_sets_error_status_on_llm_call(self, tracer):
        with pytest.raises(TimeoutError):
            with tracer.start_task("root"):
                with tracer.start_llm_call("gpt-4o") as llm_span:
                    raise TimeoutError("timeout")
        assert llm_span.status is SpanStatus.ERROR

    def test_exception_sets_error_status_on_reasoning(self, tracer):
        with pytest.raises(ValueError):
            with tracer.start_task("root"):
                with tracer.start_reasoning() as span:
                    raise ValueError("bad")
        assert span.status is SpanStatus.ERROR

    def test_exception_propagates_out(self, tracer):
        with pytest.raises(RuntimeError, match="boom"):
            with tracer.start_task("fail"):
                raise RuntimeError("boom")

    def test_span_still_recorded_on_exception(self, tracer):
        with pytest.raises(RuntimeError):
            with tracer.start_task("fail"):
                raise RuntimeError("x")
        assert len(tracer.get_spans()) == 1

    def test_nested_exception_records_all_spans(self, tracer):
        with pytest.raises(RuntimeError):
            with tracer.start_task("root"):
                with tracer.start_llm_call("m"):
                    raise RuntimeError("inner")
        # Both spans should be recorded
        assert len(tracer.get_spans()) == 2

    # -- Context manager behavior --

    def test_span_not_finished_inside_with_block(self, tracer):
        with tracer.start_task("active") as span:
            assert span.end_time_ns == 0
            assert span.status is SpanStatus.UNSET

    def test_span_finished_after_with_block(self, tracer):
        with tracer.start_task("done") as span:
            pass
        assert span.end_time_ns > 0
        assert span.status is SpanStatus.OK

    # -- get_spans / clear_spans --

    def test_get_spans_returns_copy(self, tracer):
        with tracer.start_task("t1"):
            pass
        spans = tracer.get_spans()
        spans.clear()
        assert len(tracer.get_spans()) == 1

    def test_clear_spans(self, tracer):
        with tracer.start_task("t1"):
            pass
        tracer.clear_spans()
        assert tracer.get_spans() == []

    # -- Exporter integration --

    def test_exporter_receives_spans(self, tracer):
        exported = []

        class ListExporter:
            def export_span(self, span):
                exported.append(span)

        tracer.add_exporter(ListExporter())
        with tracer.start_task("t"):
            with tracer.start_llm_call("m"):
                pass
        # Two spans: llm_call finishes first, then task
        assert len(exported) == 2
        assert exported[0].kind is AgentSpanKind.LLM_CALL
        assert exported[1].kind is AgentSpanKind.TASK

    def test_multiple_exporters(self, tracer):
        results_a, results_b = [], []

        class A:
            def export_span(self, span):
                results_a.append(span)

        class B:
            def export_span(self, span):
                results_b.append(span)

        tracer.add_exporter(A())
        tracer.add_exporter(B())
        with tracer.start_task("t"):
            pass
        assert len(results_a) == 1
        assert len(results_b) == 1

    # -- Full workflow test --

    def test_full_agent_workflow(self, tracer):
        """Simulate a realistic agent workflow and verify the trace structure."""
        with tracer.start_task("Summarize article") as task_span:
            with tracer.start_planning("decompose") as plan_span:
                plan_span.set_attribute("steps", 3)

            with tracer.start_retrieval("fetch_article") as ret_span:
                ret_span.set_attribute("source", "arxiv")

            with tracer.start_llm_call("gpt-4o") as llm_span:
                llm_span.set_attribute(ATTR_LLM_INPUT_TOKENS, 2000)
                llm_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 500)

            with tracer.start_tool_call("save_file") as tool_span:
                tool_span.set_attribute("tool.input", "/tmp/summary.txt")

        spans = tracer.get_spans()
        assert len(spans) == 5

        # All share the same trace_id
        trace_ids = {s.trace_id for s in spans}
        assert len(trace_ids) == 1

        # Task span is the root
        assert task_span.parent_span_id is None
        # All children point to task_span
        for child in [plan_span, ret_span, llm_span, tool_span]:
            assert child.parent_span_id == task_span.span_id

        # All statuses should be OK
        for s in spans:
            assert s.status is SpanStatus.OK

        # LLM cost should be calculated
        assert llm_span.cost_usd > 0

        # Tool should be marked successful
        assert tool_span.attributes[ATTR_TOOL_SUCCESS] is True
