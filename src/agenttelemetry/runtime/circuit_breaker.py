"""Telemetry-driven circuit breaker for agent execution.

Monitors spans in real-time via OTel SpanProcessor and triggers
configurable actions when fault patterns are detected. Transforms
passive observability into active runtime control.

This is the novel runtime mechanism that distinguishes AgentTelemetry
from a simple attribute naming convention.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor

from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    DELEGATION_SOURCE_AGENT,
    DELEGATION_TARGET_AGENT,
    LLM_COST,
    LLM_INPUT_TOKENS,
    TOOL_INPUT,
    TOOL_NAME,
    AgentSpanKind,
)


class CircuitAction(Enum):
    """Actions the circuit breaker can take."""
    LOG = "log"
    CALLBACK = "callback"
    RAISE = "raise"


@dataclass
class CircuitPolicy:
    """A single detection policy."""
    name: str
    description: str
    action: CircuitAction = CircuitAction.CALLBACK
    callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    enabled: bool = True


@dataclass
class _TraceState:
    """Per-trace state maintained by the circuit breaker."""
    tool_calls: List[str] = field(default_factory=list)
    tool_inputs: List[str] = field(default_factory=list)
    cumulative_cost: float = 0.0
    input_token_history: List[int] = field(default_factory=list)
    delegation_graph: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    reasoning_count: int = 0
    triggered_policies: Set[str] = field(default_factory=set)


class AgentCircuitBreaker(SpanProcessor):
    """Real-time telemetry-driven circuit breaker.

    Intercepts spans as they complete and checks for fault patterns
    using the agent-specific span kinds. When a pattern matches,
    fires a configurable callback.

    This is impossible without agent-specific span kinds: vanilla OTel
    INTERNAL spans carry no semantic information about whether a span
    is a reasoning step, a tool call, or a delegation handoff.

    Usage::

        breaker = AgentCircuitBreaker()
        breaker.add_policy(ReasoningLoopPolicy(max_repeats=3, callback=my_handler))
        breaker.add_policy(CostExplosionPolicy(threshold=1.0, callback=my_handler))

        provider = TracerProvider()
        provider.add_span_processor(breaker)

    Policies:
    - reasoning_loop: N consecutive identical tool calls → fire
    - cost_explosion: cumulative cost > threshold → fire
    - context_overflow: token growth > factor for N calls → fire
    - delegation_cycle: A→B→A delegation detected → fire
    """

    def __init__(self):
        self._traces: Dict[str, _TraceState] = {}
        self._policies: List[CircuitPolicy] = []
        self._lock = threading.Lock()
        self._fire_count = 0

        # Default policies
        self._reasoning_loop_threshold = 3
        self._cost_threshold = 1.0
        self._token_growth_factor = 2.0
        self._token_growth_streak = 2

    def add_policy(self, policy: CircuitPolicy) -> None:
        """Register a detection policy."""
        self._policies.append(policy)

    def configure_reasoning_loop(
        self, max_repeats: int = 3, callback: Optional[Callable] = None
    ) -> None:
        """Configure reasoning loop detection."""
        self._reasoning_loop_threshold = max_repeats
        self.add_policy(CircuitPolicy(
            name="reasoning_loop",
            description=f"Detect {max_repeats}+ consecutive identical tool calls",
            action=CircuitAction.CALLBACK if callback else CircuitAction.LOG,
            callback=callback,
        ))

    def configure_cost_explosion(
        self, threshold: float = 1.0, callback: Optional[Callable] = None
    ) -> None:
        """Configure cost explosion detection."""
        self._cost_threshold = threshold
        self.add_policy(CircuitPolicy(
            name="cost_explosion",
            description=f"Detect cumulative cost > ${threshold}",
            action=CircuitAction.CALLBACK if callback else CircuitAction.LOG,
            callback=callback,
        ))

    def configure_context_overflow(
        self, growth_factor: float = 2.0, streak: int = 2,
        callback: Optional[Callable] = None
    ) -> None:
        """Configure context overflow detection."""
        self._token_growth_factor = growth_factor
        self._token_growth_streak = streak
        self.add_policy(CircuitPolicy(
            name="context_overflow",
            description=f"Detect {growth_factor}x token growth for {streak}+ calls",
            action=CircuitAction.CALLBACK if callback else CircuitAction.LOG,
            callback=callback,
        ))

    def configure_delegation_cycle(
        self, callback: Optional[Callable] = None
    ) -> None:
        """Configure delegation cycle detection."""
        self.add_policy(CircuitPolicy(
            name="delegation_cycle",
            description="Detect A→B→A delegation cycles",
            action=CircuitAction.CALLBACK if callback else CircuitAction.LOG,
            callback=callback,
        ))

    @property
    def fire_count(self) -> int:
        """Number of times any policy has fired."""
        return self._fire_count

    def on_start(self, span: ReadableSpan, parent_context=None) -> None:
        """Called when a span starts. No-op for circuit breaker."""
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends. Check for fault patterns."""
        if span.attributes is None:
            return

        kind = span.attributes.get(AGENT_SPAN_KIND, "")
        if not kind:
            return

        trace_id = format(span.context.trace_id, "032x")

        with self._lock:
            if trace_id not in self._traces:
                self._traces[trace_id] = _TraceState()
            state = self._traces[trace_id]

        # Update state based on span kind
        if kind == AgentSpanKind.TOOL_CALL:
            tool_name = str(span.attributes.get(TOOL_NAME, ""))
            tool_input = str(span.attributes.get(TOOL_INPUT, ""))
            state.tool_calls.append(tool_name)
            state.tool_inputs.append(tool_input)
            self._check_reasoning_loop(trace_id, state)

        elif kind == AgentSpanKind.LLM_CALL:
            cost = float(span.attributes.get(LLM_COST, 0) or 0)
            state.cumulative_cost += cost
            input_tokens = int(span.attributes.get(LLM_INPUT_TOKENS, 0) or 0)
            if input_tokens > 0:
                state.input_token_history.append(input_tokens)
            self._check_cost_explosion(trace_id, state)
            self._check_context_overflow(trace_id, state)

        elif kind == AgentSpanKind.DELEGATION:
            source = str(span.attributes.get(DELEGATION_SOURCE_AGENT, ""))
            target = str(span.attributes.get(DELEGATION_TARGET_AGENT, ""))
            if source and target:
                state.delegation_graph[source].add(target)
                self._check_delegation_cycle(trace_id, state)

        elif kind == AgentSpanKind.REASONING:
            state.reasoning_count += 1

    def _check_reasoning_loop(self, trace_id: str, state: _TraceState) -> None:
        """Check for N consecutive identical tool calls."""
        n = self._reasoning_loop_threshold
        if len(state.tool_calls) < n:
            return
        recent = state.tool_calls[-n:]
        recent_inputs = state.tool_inputs[-n:]
        if len(set(recent)) == 1 and len(set(recent_inputs)) == 1:
            self._fire("reasoning_loop", trace_id, {
                "tool": recent[0],
                "input": recent_inputs[0],
                "count": n,
            })

    def _check_cost_explosion(self, trace_id: str, state: _TraceState) -> None:
        """Check if cumulative cost exceeds threshold."""
        if state.cumulative_cost > self._cost_threshold:
            self._fire("cost_explosion", trace_id, {
                "cumulative_cost": state.cumulative_cost,
                "threshold": self._cost_threshold,
            })

    def _check_context_overflow(self, trace_id: str, state: _TraceState) -> None:
        """Check for sustained token growth."""
        history = state.input_token_history
        streak_needed = self._token_growth_streak
        if len(history) < streak_needed + 1:
            return
        streak = 0
        for i in range(len(history) - 1, 0, -1):
            if history[i - 1] > 0 and history[i] >= history[i - 1] * self._token_growth_factor:
                streak += 1
            else:
                break
        if streak >= streak_needed:
            self._fire("context_overflow", trace_id, {
                "token_history": history[-streak_needed - 1:],
                "growth_factor": self._token_growth_factor,
            })

    def _check_delegation_cycle(self, trace_id: str, state: _TraceState) -> None:
        """Check for cycles in delegation graph via DFS."""
        graph = state.delegation_graph
        visited: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            if node in path:
                idx = path.index(node)
                return path[idx:] + [node]
            if node in visited:
                return None
            visited.add(node)
            path.append(node)
            for target in graph.get(node, set()):
                cycle = dfs(target)
                if cycle:
                    return cycle
            path.pop()
            return None

        for start in graph:
            visited.clear()
            path.clear()
            cycle = dfs(start)
            if cycle:
                self._fire("delegation_cycle", trace_id, {"cycle": cycle})
                return

    def _fire(self, policy_name: str, trace_id: str, details: Dict[str, Any]) -> None:
        """Fire a policy — call the registered callback."""
        state = self._traces.get(trace_id)
        if state and policy_name in state.triggered_policies:
            return  # Don't fire same policy twice per trace
        if state:
            state.triggered_policies.add(policy_name)

        self._fire_count += 1

        for policy in self._policies:
            if policy.name == policy_name and policy.enabled:
                if policy.action == CircuitAction.CALLBACK and policy.callback:
                    policy.callback(trace_id, details)
                elif policy.action == CircuitAction.RAISE:
                    raise RuntimeError(
                        f"Circuit breaker fired: {policy_name} in trace {trace_id}: {details}"
                    )

    def shutdown(self) -> None:
        """Clean up state."""
        self._traces.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
