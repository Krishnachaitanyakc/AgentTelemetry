"""Context propagation for multi-agent tracing.

Extends W3C trace context for multi-agent delegation by adding
agent-specific information to OTel baggage.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from opentelemetry import baggage, context, trace
from opentelemetry.propagate import inject, extract
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.composite import CompositePropagator


# Baggage keys for agent context
AGENT_ID_KEY = "agenttelemetry.agent_id"
PARENT_AGENT_ID_KEY = "agenttelemetry.parent_agent_id"


class AgentContextPropagator:
    """Manages trace context propagation across agent boundaries.

    Wraps OTel's W3C trace context + baggage propagation with
    agent-specific metadata (agent_id, parent_agent_id).
    """

    def __init__(self) -> None:
        self._propagator = CompositePropagator([
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
        ])

    def inject_context(
        self,
        carrier: Dict[str, str],
        agent_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        ctx: Optional[context.Context] = None,
    ) -> Dict[str, str]:
        """Inject trace context and agent metadata into a carrier dict.

        Use this when sending a message or request to another agent.

        Args:
            carrier: Mutable dict to inject headers into (e.g., HTTP headers).
            agent_id: ID of the current agent.
            parent_agent_id: ID of the parent agent (if delegating).
            ctx: Optional OTel context. Uses current context if not provided.

        Returns:
            The carrier dict with injected headers.
        """
        active_ctx = ctx or context.get_current()

        if agent_id:
            active_ctx = baggage.set_baggage(AGENT_ID_KEY, agent_id, context=active_ctx)
        if parent_agent_id:
            active_ctx = baggage.set_baggage(PARENT_AGENT_ID_KEY, parent_agent_id, context=active_ctx)

        self._propagator.inject(carrier, context=active_ctx)
        return carrier

    def extract_context(
        self,
        carrier: Dict[str, str],
    ) -> context.Context:
        """Extract trace context and agent metadata from a carrier dict.

        Use this when receiving a message or request from another agent.

        Args:
            carrier: Dict containing propagated headers.

        Returns:
            OTel Context with restored trace context and baggage.
        """
        return self._propagator.extract(carrier)

    @staticmethod
    def get_agent_id(ctx: Optional[context.Context] = None) -> Optional[str]:
        """Get the current agent ID from baggage."""
        return baggage.get_baggage(AGENT_ID_KEY, context=ctx)

    @staticmethod
    def get_parent_agent_id(ctx: Optional[context.Context] = None) -> Optional[str]:
        """Get the parent agent ID from baggage."""
        return baggage.get_baggage(PARENT_AGENT_ID_KEY, context=ctx)

    @staticmethod
    def set_agent_id(
        agent_id: str,
        ctx: Optional[context.Context] = None,
    ) -> context.Context:
        """Set the agent ID in baggage and return the new context."""
        return baggage.set_baggage(AGENT_ID_KEY, agent_id, context=ctx)

    @staticmethod
    def set_parent_agent_id(
        parent_agent_id: str,
        ctx: Optional[context.Context] = None,
    ) -> context.Context:
        """Set the parent agent ID in baggage and return the new context."""
        return baggage.set_baggage(PARENT_AGENT_ID_KEY, parent_agent_id, context=ctx)
