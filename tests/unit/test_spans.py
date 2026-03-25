"""Unit tests for agenttelemetry.core.spans."""

import pytest
from opentelemetry.trace import StatusCode

from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    AgentSpanKind,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_INPUT_TOKENS,
    LLM_OUTPUT_TOKENS,
    LLM_TOTAL_TOKENS,
    LLM_COST,
    LLM_TEMPERATURE,
    LLM_LATENCY_MS,
    LLM_PROMPT,
    LLM_COMPLETION,
    TOOL_NAME,
    TOOL_INPUT,
    TOOL_OUTPUT,
    TOOL_STATUS,
    TOOL_DESCRIPTION,
    TOOL_LATENCY_MS,
    RETRIEVAL_SOURCE,
    RETRIEVAL_QUERY,
    RETRIEVAL_DOC_COUNT,
    AGENT_NAME,
    AGENT_FRAMEWORK,
    AGENT_FRAMEWORK_VERSION,
    AGENT_ROLE,
    AGENT_TASK,
    DELEGATION_SOURCE_AGENT,
    DELEGATION_TARGET_AGENT,
    MEMORY_OPERATION,
    MEMORY_KEY,
    GUARDRAIL_NAME,
    GUARDRAIL_RESULT,
    PLANNING_STRATEGY,
    PLANNING_STEP_COUNT,
    REASONING_CHAIN,
    MODEL_COSTS,
    estimate_cost,
    start_agent_span,
)


class TestAgentSpanKind:
    """Tests for the AgentSpanKind constants."""

    def test_has_all_nine_values(self):
        expected = {
            "AGENT", "LLM_CALL", "TOOL_CALL", "PLANNING", "REASONING",
            "RETRIEVAL", "GUARD_RAIL", "DELEGATION", "MEMORY",
        }
        assert AgentSpanKind._ALL == expected
        assert len(AgentSpanKind._ALL) == 9

    def test_class_attributes_match_all_set(self):
        for kind in AgentSpanKind._ALL:
            assert getattr(AgentSpanKind, kind) == kind

    def test_is_valid_returns_true_for_known(self):
        for kind in AgentSpanKind._ALL:
            assert AgentSpanKind.is_valid(kind) is True

    def test_is_valid_returns_false_for_unknown(self):
        assert AgentSpanKind.is_valid("BOGUS") is False
        assert AgentSpanKind.is_valid("") is False
        assert AgentSpanKind.is_valid("agent") is False  # case-sensitive


class TestEstimateCost:
    """Tests for the estimate_cost function."""

    def test_known_model_gpt4o(self):
        # gpt-4o: input=$2.50/1M, output=$10.00/1M
        cost = estimate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        expected = 1000 * 2.50 / 1_000_000 + 500 * 10.00 / 1_000_000
        assert cost == pytest.approx(expected)

    def test_known_model_claude_opus(self):
        # claude-3-opus: input=$15.00/1M, output=$75.00/1M
        cost = estimate_cost("claude-3-opus", input_tokens=2000, output_tokens=1000)
        expected = 2000 * 15.00 / 1_000_000 + 1000 * 75.00 / 1_000_000
        assert cost == pytest.approx(expected)

    def test_model_name_matching_is_substring(self):
        # Should match "gpt-4o" inside "gpt-4o-2024-08-06"
        cost = estimate_cost("gpt-4o-2024-08-06", input_tokens=1000, output_tokens=500)
        assert cost > 0

    def test_model_name_case_insensitive(self):
        cost = estimate_cost("GPT-4o", input_tokens=1000, output_tokens=0)
        assert cost > 0

    def test_unknown_model_returns_zero(self):
        cost = estimate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=500)
        assert cost == 0.0

    def test_zero_tokens(self):
        cost = estimate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0


class TestStartAgentSpan:
    """Tests for the start_agent_span context manager."""

    def test_creates_span_with_agent_span_kind(self, tracer, memory_exporter):
        with start_agent_span("test-span", AgentSpanKind.LLM_CALL, tracer=tracer):
            pass

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.attributes[AGENT_SPAN_KIND] == "LLM_CALL"

    def test_span_name_is_set(self, tracer, memory_exporter):
        with start_agent_span("my-llm-call", AgentSpanKind.LLM_CALL, tracer=tracer):
            pass

        spans = memory_exporter.get_finished_spans()
        assert spans[0].name == "my-llm-call"

    def test_custom_attributes_are_set(self, tracer, memory_exporter):
        attrs = {LLM_MODEL: "gpt-4o", LLM_INPUT_TOKENS: 100}
        with start_agent_span("call", AgentSpanKind.LLM_CALL, tracer=tracer, attributes=attrs):
            pass

        span = memory_exporter.get_finished_spans()[0]
        assert span.attributes[LLM_MODEL] == "gpt-4o"
        assert span.attributes[LLM_INPUT_TOKENS] == 100

    def test_yields_active_span(self, tracer, memory_exporter):
        with start_agent_span("call", AgentSpanKind.AGENT, tracer=tracer) as span:
            span.set_attribute("custom.key", "value")

        exported = memory_exporter.get_finished_spans()[0]
        assert exported.attributes["custom.key"] == "value"

    def test_records_exception_on_error(self, tracer, memory_exporter):
        with pytest.raises(ValueError, match="test error"):
            with start_agent_span("fail", AgentSpanKind.TOOL_CALL, tracer=tracer):
                raise ValueError("test error")

        span = memory_exporter.get_finished_spans()[0]
        assert span.status.status_code == StatusCode.ERROR
        assert "test error" in span.status.description
        assert len(span.events) > 0
        assert span.events[0].name == "exception"

    def test_nested_spans_create_parent_child(self, tracer, memory_exporter):
        with start_agent_span("parent", AgentSpanKind.AGENT, tracer=tracer):
            with start_agent_span("child", AgentSpanKind.LLM_CALL, tracer=tracer):
                pass

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 2
        child = [s for s in spans if s.name == "child"][0]
        parent = [s for s in spans if s.name == "parent"][0]
        assert child.parent.span_id == parent.context.span_id


class TestSemanticAttributes:
    """Verify all semantic attribute constants are defined."""

    def test_llm_attributes_defined(self):
        assert LLM_MODEL == "llm.model"
        assert LLM_PROVIDER == "llm.provider"
        assert LLM_INPUT_TOKENS == "llm.input_tokens"
        assert LLM_OUTPUT_TOKENS == "llm.output_tokens"
        assert LLM_TOTAL_TOKENS == "llm.total_tokens"
        assert LLM_COST == "llm.cost"
        assert LLM_TEMPERATURE == "llm.temperature"
        assert LLM_LATENCY_MS == "llm.latency_ms"
        assert LLM_PROMPT == "llm.prompt"
        assert LLM_COMPLETION == "llm.completion"

    def test_tool_attributes_defined(self):
        assert TOOL_NAME == "tool.name"
        assert TOOL_INPUT == "tool.input"
        assert TOOL_OUTPUT == "tool.output"
        assert TOOL_STATUS == "tool.status"
        assert TOOL_DESCRIPTION == "tool.description"
        assert TOOL_LATENCY_MS == "tool.latency_ms"

    def test_retrieval_attributes_defined(self):
        assert RETRIEVAL_SOURCE == "retrieval.source"
        assert RETRIEVAL_QUERY == "retrieval.query"
        assert RETRIEVAL_DOC_COUNT == "retrieval.doc_count"

    def test_agent_attributes_defined(self):
        assert AGENT_NAME == "agent.name"
        assert AGENT_FRAMEWORK == "agent.framework"
        assert AGENT_FRAMEWORK_VERSION == "agent.framework.version"
        assert AGENT_ROLE == "agent.role"
        assert AGENT_TASK == "agent.task"

    def test_delegation_attributes_defined(self):
        assert DELEGATION_SOURCE_AGENT == "delegation.source_agent"
        assert DELEGATION_TARGET_AGENT == "delegation.target_agent"

    def test_memory_attributes_defined(self):
        assert MEMORY_OPERATION == "memory.operation"
        assert MEMORY_KEY == "memory.key"

    def test_guardrail_attributes_defined(self):
        assert GUARDRAIL_NAME == "guardrail.name"
        assert GUARDRAIL_RESULT == "guardrail.result"

    def test_planning_attributes_defined(self):
        assert PLANNING_STRATEGY == "planning.strategy"
        assert PLANNING_STEP_COUNT == "planning.step_count"

    def test_reasoning_attributes_defined(self):
        assert REASONING_CHAIN == "reasoning.chain"
