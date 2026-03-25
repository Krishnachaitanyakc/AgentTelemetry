"""Agent-specific span definitions built on OpenTelemetry.

OTel's SpanKind enum is fixed (5 values). We represent our 9 agent-specific
span kinds as semantic attributes on INTERNAL spans. This module provides
the span kind constants, semantic attribute keys, and helper functions.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Sequence

from opentelemetry import trace
from opentelemetry.trace import SpanKind, StatusCode, Tracer

# Custom attribute key for agent span kind
AGENT_SPAN_KIND = "agenttelemetry.span.kind"


class AgentSpanKind:
    """9 agent-specific span kinds stored as string attribute values."""

    AGENT = "AGENT"
    LLM_CALL = "LLM_CALL"
    TOOL_CALL = "TOOL_CALL"
    PLANNING = "PLANNING"
    REASONING = "REASONING"
    RETRIEVAL = "RETRIEVAL"
    GUARD_RAIL = "GUARD_RAIL"
    DELEGATION = "DELEGATION"
    MEMORY = "MEMORY"

    _ALL = {
        "AGENT", "LLM_CALL", "TOOL_CALL", "PLANNING", "REASONING",
        "RETRIEVAL", "GUARD_RAIL", "DELEGATION", "MEMORY",
    }

    @classmethod
    def is_valid(cls, kind: str) -> bool:
        return kind in cls._ALL


# ---------------------------------------------------------------------------
# Semantic attribute keys per span kind
# ---------------------------------------------------------------------------

# LLM_CALL attributes
LLM_MODEL = "llm.model"
LLM_PROVIDER = "llm.provider"
LLM_INPUT_TOKENS = "llm.input_tokens"
LLM_OUTPUT_TOKENS = "llm.output_tokens"
LLM_TOTAL_TOKENS = "llm.total_tokens"
LLM_COST = "llm.cost"
LLM_TEMPERATURE = "llm.temperature"
LLM_LATENCY_MS = "llm.latency_ms"
LLM_PROMPT = "llm.prompt"
LLM_COMPLETION = "llm.completion"

# TOOL_CALL attributes
TOOL_NAME = "tool.name"
TOOL_INPUT = "tool.input"
TOOL_OUTPUT = "tool.output"
TOOL_STATUS = "tool.status"
TOOL_DESCRIPTION = "tool.description"
TOOL_LATENCY_MS = "tool.latency_ms"

# RETRIEVAL attributes
RETRIEVAL_SOURCE = "retrieval.source"
RETRIEVAL_QUERY = "retrieval.query"
RETRIEVAL_DOC_COUNT = "retrieval.doc_count"
RETRIEVAL_STALENESS_SECONDS = "retrieval.staleness_seconds"

# AGENT attributes
AGENT_NAME = "agent.name"
AGENT_FRAMEWORK = "agent.framework"
AGENT_FRAMEWORK_VERSION = "agent.framework.version"
AGENT_ROLE = "agent.role"
AGENT_TASK = "agent.task"
AGENT_MISROUTED = "agent.misrouted"
AGENT_EXPECTED_NAME = "agent.expected_name"

# DELEGATION attributes
DELEGATION_SOURCE_AGENT = "delegation.source_agent"
DELEGATION_TARGET_AGENT = "delegation.target_agent"

# MEMORY attributes
MEMORY_OPERATION = "memory.operation"
MEMORY_KEY = "memory.key"
MEMORY_CORRUPTED = "memory.corrupted"

# GUARD_RAIL attributes
GUARDRAIL_NAME = "guardrail.name"
GUARDRAIL_RESULT = "guardrail.result"

# PLANNING attributes
PLANNING_STRATEGY = "planning.strategy"
PLANNING_STEP_COUNT = "planning.step_count"

# REASONING attributes
REASONING_CHAIN = "reasoning.chain"


# ---------------------------------------------------------------------------
# Cost estimation (USD per 1M tokens)
# ---------------------------------------------------------------------------

MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-haiku-4": {"input": 0.80, "output": 4.00},
    # New models added for real LLM experiment
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-5": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for an LLM call."""
    model_key = model.lower().strip()
    for known_model, costs in MODEL_COSTS.items():
        if known_model in model_key:
            return (
                input_tokens * costs["input"] / 1_000_000
                + output_tokens * costs["output"] / 1_000_000
            )
    return 0.0


# ---------------------------------------------------------------------------
# Helper: start_agent_span
# ---------------------------------------------------------------------------

@contextmanager
def start_agent_span(
    name: str,
    kind: str,
    tracer: Optional[Tracer] = None,
    attributes: Optional[Dict[str, Any]] = None,
    parent_context: Optional[trace.Context] = None,
) -> Generator[trace.Span, None, None]:
    """Start an OTel span with agent-specific semantic attributes.

    Args:
        name: Span name.
        kind: One of AgentSpanKind values (e.g. "LLM_CALL").
        tracer: OTel Tracer instance. Uses global tracer if not provided.
        attributes: Additional span attributes.
        parent_context: Optional parent context for cross-agent linking.

    Yields:
        The active OTel Span.
    """
    if tracer is None:
        tracer = trace.get_tracer("agenttelemetry", "0.1.0")

    span_attrs = {AGENT_SPAN_KIND: kind}
    if attributes:
        span_attrs.update(attributes)

    kwargs: Dict[str, Any] = {
        "kind": SpanKind.INTERNAL,
        "attributes": span_attrs,
    }
    if parent_context is not None:
        kwargs["context"] = parent_context

    with tracer.start_as_current_span(name, **kwargs) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
