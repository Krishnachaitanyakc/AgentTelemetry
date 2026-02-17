"""Event types for agent telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class EventType(Enum):
    """Categorizes events that occur within agent spans."""

    LLM_START = "llm_start"
    LLM_END = "llm_end"
    LLM_STREAM_CHUNK = "llm_stream_chunk"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_MESSAGE = "agent_message"
    PLANNING_START = "planning_start"
    PLANNING_END = "planning_end"
    RETRIEVAL_HIT = "retrieval_hit"
    HUMAN_FEEDBACK = "human_feedback"
    ERROR = "error"
    WARNING = "warning"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"
    COST_THRESHOLD = "cost_threshold"
    CUSTOM = "custom"


@dataclass
class AgentEvent:
    """A timestamped event within an agent span.

    Events capture discrete occurrences during span execution, such as
    when a guardrail fires, an error occurs, or a cost threshold is hit.
    """

    name: str
    event_type: EventType
    timestamp_ns: int
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "event_type": self.event_type.value,
            "timestamp_ns": self.timestamp_ns,
            "attributes": self.attributes,
        }
