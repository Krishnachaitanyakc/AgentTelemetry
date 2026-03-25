"""Custom (manual) instrumentation adapter.

Provides convenience functions that wrap ``start_agent_span`` with pre-filled
span kinds and common attributes.  Use this when your framework is not
supported or when you want fine-grained control.

Unlike the other adapters this module does not implement ``BaseInstrumentor``
because there is nothing to instrument automatically — it is a purely manual
API.  It re-exports ``start_agent_span`` and adds typed helpers.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from opentelemetry import trace
from opentelemetry.trace import Tracer

from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    AGENT_FRAMEWORK,
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_TASK,
    AgentSpanKind,
    DELEGATION_SOURCE_AGENT,
    DELEGATION_TARGET_AGENT,
    GUARDRAIL_NAME,
    GUARDRAIL_RESULT,
    LLM_COMPLETION,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    LLM_PROMPT,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
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
from agenttelemetry.core.privacy import PrivacyLevel, filter_attributes, should_capture_content

# Re-export the core helper so users can import from one place
__all__ = [
    "start_agent_span",
    "start_llm_span",
    "start_tool_span",
    "start_retrieval_span",
    "start_agent_span_ctx",
    "start_planning_span",
    "start_reasoning_span",
    "start_guardrail_span",
    "start_delegation_span",
    "start_memory_span",
]


@contextmanager
def start_llm_span(
    name: str,
    model: str,
    provider: str = "",
    *,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost: Optional[float] = None,
    temperature: Optional[float] = None,
    prompt: Optional[str] = None,
    completion: Optional[str] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start an LLM_CALL span with common LLM attributes pre-filled.

    Example::

        with start_llm_span("gpt-4o call", model="gpt-4o", provider="openai") as span:
            response = call_llm(...)
            span.set_attribute("llm.output_tokens", response.usage.output_tokens)
    """
    attrs: Dict[str, Any] = {
        LLM_MODEL: model,
        LLM_PROVIDER: provider,
    }
    if input_tokens is not None:
        attrs[LLM_INPUT_TOKENS] = input_tokens
    if output_tokens is not None:
        attrs[LLM_OUTPUT_TOKENS] = output_tokens
    if input_tokens is not None and output_tokens is not None:
        attrs[LLM_TOTAL_TOKENS] = input_tokens + output_tokens
    if cost is not None:
        attrs[LLM_COST] = cost
    if temperature is not None:
        attrs[LLM_TEMPERATURE] = temperature
    if prompt is not None:
        attrs[LLM_PROMPT] = prompt
    if completion is not None:
        attrs[LLM_COMPLETION] = completion
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.LLM_CALL, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_tool_span(
    name: str,
    tool_name: str,
    *,
    tool_input: Optional[str] = None,
    tool_output: Optional[str] = None,
    tool_status: Optional[str] = None,
    description: Optional[str] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start a TOOL_CALL span with common tool attributes pre-filled."""
    attrs: Dict[str, Any] = {TOOL_NAME: tool_name}
    if tool_input is not None:
        attrs[TOOL_INPUT] = tool_input
    if tool_output is not None:
        attrs[TOOL_OUTPUT] = tool_output
    if tool_status is not None:
        attrs[TOOL_STATUS] = tool_status
    if description is not None:
        attrs[TOOL_DESCRIPTION] = description
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.TOOL_CALL, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_retrieval_span(
    name: str,
    source: str,
    *,
    query: Optional[str] = None,
    doc_count: Optional[int] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start a RETRIEVAL span with common retrieval attributes pre-filled."""
    attrs: Dict[str, Any] = {RETRIEVAL_SOURCE: source}
    if query is not None:
        attrs[RETRIEVAL_QUERY] = query
    if doc_count is not None:
        attrs[RETRIEVAL_DOC_COUNT] = doc_count
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.RETRIEVAL, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_agent_span_ctx(
    name: str,
    agent_name: str,
    *,
    framework: Optional[str] = None,
    role: Optional[str] = None,
    task: Optional[str] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start an AGENT span with common agent attributes pre-filled."""
    attrs: Dict[str, Any] = {AGENT_NAME: agent_name}
    if framework is not None:
        attrs[AGENT_FRAMEWORK] = framework
    if role is not None:
        attrs[AGENT_ROLE] = role
    if task is not None:
        attrs[AGENT_TASK] = task
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.AGENT, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_planning_span(
    name: str,
    *,
    strategy: Optional[str] = None,
    step_count: Optional[int] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start a PLANNING span."""
    attrs: Dict[str, Any] = {}
    if strategy is not None:
        attrs[PLANNING_STRATEGY] = strategy
    if step_count is not None:
        attrs[PLANNING_STEP_COUNT] = step_count
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.PLANNING, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_reasoning_span(
    name: str,
    *,
    chain: Optional[str] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start a REASONING span."""
    attrs: Dict[str, Any] = {}
    if chain is not None:
        attrs[REASONING_CHAIN] = chain
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.REASONING, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_guardrail_span(
    name: str,
    guardrail_name: str,
    *,
    result: Optional[str] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start a GUARD_RAIL span."""
    attrs: Dict[str, Any] = {GUARDRAIL_NAME: guardrail_name}
    if result is not None:
        attrs[GUARDRAIL_RESULT] = result
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.GUARD_RAIL, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_delegation_span(
    name: str,
    source_agent: str,
    target_agent: str,
    *,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start a DELEGATION span."""
    attrs: Dict[str, Any] = {
        DELEGATION_SOURCE_AGENT: source_agent,
        DELEGATION_TARGET_AGENT: target_agent,
    }
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.DELEGATION, tracer=tracer, attributes=filtered) as span:
        yield span


@contextmanager
def start_memory_span(
    name: str,
    operation: str,
    *,
    key: Optional[str] = None,
    tracer: Optional[Tracer] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Start a MEMORY span."""
    attrs: Dict[str, Any] = {MEMORY_OPERATION: operation}
    if key is not None:
        attrs[MEMORY_KEY] = key
    if extra_attributes:
        attrs.update(extra_attributes)

    filtered = filter_attributes(attrs, privacy_level)
    with start_agent_span(name, AgentSpanKind.MEMORY, tracer=tracer, attributes=filtered) as span:
        yield span
