"""Core tracing API for AgentTelemetry.

Maps agent concepts to observability primitives following OpenTelemetry conventions:

    Service    → Agent
    Trace      → AgentTrace  (full task execution from start to finish)
    Span       → AgentSpan   (one reasoning step, LLM call, or tool invocation)
    SpanKind   → AgentSpanKind (TASK, REASONING, LLM_CALL, TOOL_CALL, etc.)
    Attributes → Semantic conventions (agent.*, llm.*, tool.*)

Design decisions:
    1. Standalone — no OpenTelemetry dependency required for core tracing
    2. OTel-compatible — spans map 1:1 to OTel spans when otlp exporter is used
    3. Privacy-first — prompt/completion capture is opt-in via capture_content=True
    4. Multi-agent — context propagation across agent boundaries via trace_id
    5. Cost-aware — built-in token counting and cost estimation
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, List, Optional

from agenttelemetry.core.events import AgentEvent, EventType


class AgentSpanKind(Enum):
    """Categorizes the type of work an agent span represents.

    Mirrors the concept of SpanKind in OpenTelemetry but with agent-specific
    semantics. Each kind maps to a distinct phase in agent execution.
    """

    TASK = "task"  # Top-level task (root span)
    REASONING = "reasoning"  # Agent reasoning / chain-of-thought
    LLM_CALL = "llm_call"  # Call to a language model
    TOOL_CALL = "tool_call"  # Tool / function invocation
    PLANNING = "planning"  # Task decomposition / planning step
    REFLECTION = "reflection"  # Self-evaluation / critique
    RETRIEVAL = "retrieval"  # RAG / knowledge retrieval
    AGENT_COMM = "agent_comm"  # Inter-agent communication
    HUMAN_INPUT = "human_input"  # Human-in-the-loop interaction


class SpanStatus(Enum):
    """Execution status of a span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# Semantic convention attribute keys
# ---------------------------------------------------------------------------

# Agent attributes
ATTR_AGENT_NAME = "agent.name"
ATTR_AGENT_FRAMEWORK = "agent.framework"
ATTR_AGENT_FRAMEWORK_VERSION = "agent.framework.version"
ATTR_AGENT_ROLE = "agent.role"
ATTR_AGENT_TASK = "agent.task"

# LLM attributes
ATTR_LLM_MODEL = "llm.model"
ATTR_LLM_PROVIDER = "llm.provider"
ATTR_LLM_INPUT_TOKENS = "llm.input_tokens"
ATTR_LLM_OUTPUT_TOKENS = "llm.output_tokens"
ATTR_LLM_TOTAL_TOKENS = "llm.total_tokens"
ATTR_LLM_TEMPERATURE = "llm.temperature"
ATTR_LLM_COST_USD = "llm.cost_usd"
ATTR_LLM_LATENCY_MS = "llm.latency_ms"
ATTR_LLM_PROMPT = "llm.prompt"  # opt-in
ATTR_LLM_COMPLETION = "llm.completion"  # opt-in

# Tool attributes
ATTR_TOOL_NAME = "tool.name"
ATTR_TOOL_DESCRIPTION = "tool.description"
ATTR_TOOL_INPUT = "tool.input"
ATTR_TOOL_OUTPUT = "tool.output"
ATTR_TOOL_SUCCESS = "tool.success"
ATTR_TOOL_ERROR = "tool.error"
ATTR_TOOL_LATENCY_MS = "tool.latency_ms"

# Inter-agent attributes
ATTR_INTERACTION_TYPE = "agent.interaction.type"
ATTR_INTERACTION_SOURCE = "agent.interaction.source_agent"
ATTR_INTERACTION_TARGET = "agent.interaction.target_agent"


# ---------------------------------------------------------------------------
# Cost estimation (USD per 1M tokens, approximate as of 2025)
# ---------------------------------------------------------------------------

_MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for an LLM call."""
    # Normalize model name
    model_key = model.lower().strip()
    for known_model, costs in _MODEL_COSTS.items():
        if known_model in model_key:
            return (
                input_tokens * costs["input"] / 1_000_000
                + output_tokens * costs["output"] / 1_000_000
            )
    return 0.0  # Unknown model


# ---------------------------------------------------------------------------
# AgentSpan
# ---------------------------------------------------------------------------


@dataclass
class AgentSpan:
    """A single unit of work in an agent's execution.

    Analogous to an OpenTelemetry Span. Represents one step such as an LLM
    call, tool invocation, reasoning step, or inter-agent message.
    """

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: AgentSpanKind
    start_time_ns: int
    end_time_ns: int = 0
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[AgentEvent] = field(default_factory=list)

    # Convenience accessors
    @property
    def duration_ms(self) -> float:
        if self.end_time_ns == 0:
            return 0.0
        return (self.end_time_ns - self.start_time_ns) / 1_000_000

    @property
    def agent_name(self) -> Optional[str]:
        return self.attributes.get(ATTR_AGENT_NAME)

    @property
    def model(self) -> Optional[str]:
        return self.attributes.get(ATTR_LLM_MODEL)

    @property
    def input_tokens(self) -> int:
        return self.attributes.get(ATTR_LLM_INPUT_TOKENS, 0)

    @property
    def output_tokens(self) -> int:
        return self.attributes.get(ATTR_LLM_OUTPUT_TOKENS, 0)

    @property
    def cost_usd(self) -> float:
        return self.attributes.get(ATTR_LLM_COST_USD, 0.0)

    @property
    def tool_name(self) -> Optional[str]:
        return self.attributes.get(ATTR_TOOL_NAME)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, event_type: EventType, **attrs: Any) -> None:
        self.events.append(
            AgentEvent(
                name=name,
                event_type=event_type,
                timestamp_ns=time.time_ns(),
                attributes=attrs,
            )
        )

    def set_status(self, status: SpanStatus, description: str = "") -> None:
        self.status = status
        if description:
            self.attributes["status.description"] = description

    def end(self) -> None:
        self.end_time_ns = time.time_ns()
        if self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        """Serialize span to a dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time_ns": self.start_time_ns,
            "end_time_ns": self.end_time_ns,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [e.to_dict() for e in self.events],
        }


# ---------------------------------------------------------------------------
# AgentTracer
# ---------------------------------------------------------------------------


class AgentTracer:
    """Creates and manages agent spans.

    Usage::

        tracer = AgentTracer(agent_name="researcher", framework="langchain")

        with tracer.start_task("Summarize document") as task_span:
            with tracer.start_llm_call(model="gpt-4o") as llm_span:
                llm_span.set_attribute("llm.input_tokens", 500)
                llm_span.set_attribute("llm.output_tokens", 200)
            with tracer.start_tool_call(tool_name="web_search") as tool_span:
                tool_span.set_attribute("tool.success", True)

        # Export all collected spans
        for span in tracer.get_spans():
            print(span.to_dict())
    """

    def __init__(
        self,
        agent_name: str,
        framework: str = "unknown",
        framework_version: str = "",
        capture_content: bool = False,
    ):
        self._agent_name = agent_name
        self._framework = framework
        self._framework_version = framework_version
        self._capture_content = capture_content
        self._spans: List[AgentSpan] = []
        self._active_spans: List[AgentSpan] = []
        self._exporters: list = []

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @property
    def capture_content(self) -> bool:
        return self._capture_content

    def add_exporter(self, exporter: Any) -> None:
        """Register an exporter that receives completed spans."""
        self._exporters.append(exporter)

    def get_spans(self) -> List[AgentSpan]:
        """Return all collected spans."""
        return list(self._spans)

    def clear_spans(self) -> None:
        """Clear collected spans."""
        self._spans.clear()

    def _current_trace_id(self) -> str:
        if self._active_spans:
            return self._active_spans[0].trace_id
        return uuid.uuid4().hex[:32]

    def _current_span_id(self) -> Optional[str]:
        if self._active_spans:
            return self._active_spans[-1].span_id
        return None

    def _make_span(self, name: str, kind: AgentSpanKind, **attrs: Any) -> AgentSpan:
        is_root = kind == AgentSpanKind.TASK and not self._active_spans
        trace_id = uuid.uuid4().hex[:32] if is_root else self._current_trace_id()
        span = AgentSpan(
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=self._current_span_id(),
            name=name,
            kind=kind,
            start_time_ns=time.time_ns(),
        )
        span.set_attribute(ATTR_AGENT_NAME, self._agent_name)
        span.set_attribute(ATTR_AGENT_FRAMEWORK, self._framework)
        if self._framework_version:
            span.set_attribute(ATTR_AGENT_FRAMEWORK_VERSION, self._framework_version)
        for key, value in attrs.items():
            span.set_attribute(key, value)
        return span

    def _finish_span(self, span: AgentSpan) -> None:
        span.end()
        # Auto-calculate cost for LLM calls
        if span.kind == AgentSpanKind.LLM_CALL and span.model:
            cost = estimate_cost(span.model, span.input_tokens, span.output_tokens)
            if cost > 0:
                span.set_attribute(ATTR_LLM_COST_USD, cost)
        self._spans.append(span)
        if span in self._active_spans:
            self._active_spans.remove(span)
        # Export
        for exporter in self._exporters:
            exporter.export_span(span)

    @contextmanager
    def start_task(
        self, task_name: str, **attrs: Any
    ) -> Generator[AgentSpan, None, None]:
        """Start a top-level task span (root of the trace)."""
        span = self._make_span(task_name, AgentSpanKind.TASK, **attrs)
        self._active_spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            span.add_event("exception", EventType.ERROR, error=str(exc))
            raise
        finally:
            self._finish_span(span)

    @contextmanager
    def start_llm_call(
        self, model: str = "unknown", **attrs: Any
    ) -> Generator[AgentSpan, None, None]:
        """Start an LLM call span."""
        attrs[ATTR_LLM_MODEL] = model
        span = self._make_span(f"llm.{model}", AgentSpanKind.LLM_CALL, **attrs)
        self._active_spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            raise
        finally:
            self._finish_span(span)

    @contextmanager
    def start_tool_call(
        self, tool_name: str, **attrs: Any
    ) -> Generator[AgentSpan, None, None]:
        """Start a tool call span."""
        attrs[ATTR_TOOL_NAME] = tool_name
        span = self._make_span(f"tool.{tool_name}", AgentSpanKind.TOOL_CALL, **attrs)
        self._active_spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            span.set_attribute(ATTR_TOOL_SUCCESS, False)
            span.set_attribute(ATTR_TOOL_ERROR, str(exc))
            raise
        finally:
            if ATTR_TOOL_SUCCESS not in span.attributes:
                span.set_attribute(ATTR_TOOL_SUCCESS, True)
            self._finish_span(span)

    @contextmanager
    def start_reasoning(
        self, name: str = "reasoning", **attrs: Any
    ) -> Generator[AgentSpan, None, None]:
        """Start a reasoning/chain-of-thought span."""
        span = self._make_span(name, AgentSpanKind.REASONING, **attrs)
        self._active_spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            raise
        finally:
            self._finish_span(span)

    @contextmanager
    def start_planning(
        self, name: str = "planning", **attrs: Any
    ) -> Generator[AgentSpan, None, None]:
        """Start a planning/decomposition span."""
        span = self._make_span(name, AgentSpanKind.PLANNING, **attrs)
        self._active_spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            raise
        finally:
            self._finish_span(span)

    @contextmanager
    def start_retrieval(
        self, name: str = "retrieval", **attrs: Any
    ) -> Generator[AgentSpan, None, None]:
        """Start a retrieval/RAG span."""
        span = self._make_span(name, AgentSpanKind.RETRIEVAL, **attrs)
        self._active_spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            raise
        finally:
            self._finish_span(span)

    @contextmanager
    def start_agent_comm(
        self, target_agent: str, **attrs: Any
    ) -> Generator[AgentSpan, None, None]:
        """Start an inter-agent communication span."""
        attrs[ATTR_INTERACTION_SOURCE] = self._agent_name
        attrs[ATTR_INTERACTION_TARGET] = target_agent
        span = self._make_span(
            f"comm.{self._agent_name}->{target_agent}",
            AgentSpanKind.AGENT_COMM,
            **attrs,
        )
        self._active_spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            raise
        finally:
            self._finish_span(span)
