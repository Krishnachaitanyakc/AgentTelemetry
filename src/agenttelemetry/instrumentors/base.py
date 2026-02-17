"""Base instrumentor for agent frameworks.

All framework-specific instrumentors inherit from BaseInstrumentor and
implement the instrument() and uninstrument() methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from agenttelemetry.core.trace import AgentTracer
from agenttelemetry.core.metrics import AgentMetrics


class BaseInstrumentor(ABC):
    """Abstract base class for framework instrumentors.

    Instrumentors monkey-patch or hook into agent framework internals
    to automatically capture telemetry without requiring user code changes.

    Usage::

        from agenttelemetry.instrumentors.langchain import LangChainInstrumentor

        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()  # patches LangChain

        # ... use LangChain normally — telemetry is captured automatically ...

        instrumentor.uninstrument()  # removes patches
    """

    def __init__(
        self,
        tracer: Optional[AgentTracer] = None,
        metrics: Optional[AgentMetrics] = None,
        capture_content: bool = False,
    ):
        self._tracer = tracer or AgentTracer(
            agent_name=self.framework_name,
            framework=self.framework_name,
            capture_content=capture_content,
        )
        self._metrics = metrics or AgentMetrics(agent_name=self.framework_name)
        self._capture_content = capture_content
        self._instrumented = False

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Return the name of the framework being instrumented."""
        ...

    @property
    def tracer(self) -> AgentTracer:
        return self._tracer

    @property
    def metrics(self) -> AgentMetrics:
        return self._metrics

    @property
    def is_instrumented(self) -> bool:
        return self._instrumented

    @abstractmethod
    def instrument(self) -> None:
        """Apply instrumentation patches to the framework."""
        ...

    @abstractmethod
    def uninstrument(self) -> None:
        """Remove instrumentation patches."""
        ...

    def _record_llm_metrics(
        self, model: str, input_tokens: int, output_tokens: int, latency_ms: float, cost_usd: float
    ) -> None:
        """Record standard LLM metrics."""
        self._metrics.increment("agent.llm.call.count", model=model)
        self._metrics.increment("agent.llm.tokens.input", value=input_tokens, model=model)
        self._metrics.increment("agent.llm.tokens.output", value=output_tokens, model=model)
        self._metrics.increment("agent.cost.total_usd", value=cost_usd)
        self._metrics.record("agent.llm.latency_ms", latency_ms, model=model)

    def _record_tool_metrics(
        self, tool_name: str, latency_ms: float, success: bool
    ) -> None:
        """Record standard tool metrics."""
        self._metrics.increment("agent.tool.call.count", tool=tool_name)
        self._metrics.record("agent.tool.latency_ms", latency_ms, tool=tool_name)
        if not success:
            self._metrics.increment("agent.error.count", tool=tool_name)
