"""Context propagation for multi-agent tracing.

Enables trace context to flow across agent boundaries so that spans from
different agents in a multi-agent system share the same trace_id, producing
a unified end-to-end trace.

Usage::

    # Agent A creates a context
    ctx = AgentContext.from_tracer(tracer_a)

    # Serialize and send to Agent B (via message, HTTP header, etc.)
    carrier = ctx.to_carrier()

    # Agent B receives and restores context
    ctx_b = AgentContext.from_carrier(carrier)
    tracer_b.attach_context(ctx_b)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agenttelemetry.core.trace import AgentTracer


# W3C Trace Context header keys (standard)
TRACEPARENT_KEY = "traceparent"
AGENTSTATE_KEY = "agentstate"


@dataclass
class AgentContext:
    """Propagation context for cross-agent tracing.

    Follows W3C Trace Context conventions where possible, extended with
    agent-specific metadata.
    """

    trace_id: str
    parent_span_id: str
    source_agent: str = ""
    baggage: Dict[str, str] = None

    def __post_init__(self):
        if self.baggage is None:
            self.baggage = {}

    def to_carrier(self) -> Dict[str, str]:
        """Serialize context for transport (HTTP headers, message metadata)."""
        carrier = {
            TRACEPARENT_KEY: f"00-{self.trace_id}-{self.parent_span_id}-01",
            AGENTSTATE_KEY: self.source_agent,
        }
        if self.baggage:
            carrier["baggage"] = ",".join(
                f"{k}={v}" for k, v in self.baggage.items()
            )
        return carrier

    @classmethod
    def from_carrier(cls, carrier: Dict[str, str]) -> AgentContext:
        """Deserialize context from transport."""
        traceparent = carrier.get(TRACEPARENT_KEY, "")
        parts = traceparent.split("-")
        if len(parts) >= 3:
            trace_id = parts[1]
            parent_span_id = parts[2]
        else:
            trace_id = ""
            parent_span_id = ""

        source_agent = carrier.get(AGENTSTATE_KEY, "")

        baggage_str = carrier.get("baggage", "")
        baggage = {}
        if baggage_str:
            for item in baggage_str.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    baggage[k.strip()] = v.strip()

        return cls(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            source_agent=source_agent,
            baggage=baggage,
        )

    @classmethod
    def from_tracer(cls, tracer: AgentTracer) -> Optional[AgentContext]:
        """Extract current context from a tracer's active spans."""
        if not tracer._active_spans:
            return None
        active = tracer._active_spans[-1]
        return cls(
            trace_id=active.trace_id,
            parent_span_id=active.span_id,
            source_agent=tracer.agent_name,
        )
