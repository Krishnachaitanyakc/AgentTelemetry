"""Decision attribution: link tool calls to the LLM decisions that chose them.

Builds a trace tree from span dicts, then for each TOOL_CALL span finds the
parent LLM_CALL and any nearby REASONING spans to reconstruct the decision
chain.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agenttelemetry.core.spans import (
    AGENT_NAME,
    AGENT_SPAN_KIND,
    LLM_MODEL,
    REASONING_CHAIN,
    TOOL_NAME,
    AgentSpanKind,
)


@dataclass
class ToolDecision:
    """A single tool invocation linked back to the LLM that chose it."""

    tool_name: str
    tool_span_id: str
    llm_span_id: str
    llm_model: str
    agent_name: str
    reasoning: Optional[str]
    trace_id: str


class DecisionAttributor:
    """Attribute each tool call to the LLM decision that triggered it.

    Reconstructs the parent-child tree from span dicts and walks it to
    find LLM_CALL parents and REASONING siblings/ancestors.
    """

    def analyze(self, spans: List[Dict[str, Any]]) -> List[ToolDecision]:
        """Return a :class:`ToolDecision` for every TOOL_CALL span."""
        # Index spans by span_id and build children map
        by_id: Dict[str, Dict[str, Any]] = {}
        children: Dict[Optional[str], List[str]] = defaultdict(list)

        for span in spans:
            sid = span.get("span_id", "")
            by_id[sid] = span
            parent = span.get("parent_span_id")
            children[parent].append(sid)

        decisions: List[ToolDecision] = []

        for span in spans:
            kind = span.get("agent_span_kind") or ""
            if kind != AgentSpanKind.TOOL_CALL:
                continue

            attrs = span.get("attributes") or {}
            tool_name = str(attrs.get(TOOL_NAME, span.get("name", "unknown")))
            tool_span_id = span.get("span_id", "")
            trace_id = span.get("trace_id", "unknown")

            # Walk ancestors to find the closest LLM_CALL
            llm_span_id = ""
            llm_model = "unknown"
            agent_name = "unknown"
            reasoning: Optional[str] = None

            parent_id = span.get("parent_span_id")
            visited: set = set()
            while parent_id and parent_id not in visited:
                visited.add(parent_id)
                parent_span = by_id.get(parent_id)
                if parent_span is None:
                    break

                parent_kind = parent_span.get("agent_span_kind") or ""
                parent_attrs = parent_span.get("attributes") or {}

                if parent_kind == AgentSpanKind.LLM_CALL and not llm_span_id:
                    llm_span_id = parent_id
                    llm_model = str(parent_attrs.get(LLM_MODEL, "unknown"))
                    agent_name = str(parent_attrs.get(AGENT_NAME, "unknown"))

                parent_id = parent_span.get("parent_span_id")

            # If agent_name still unknown, look in tool span attrs
            if agent_name == "unknown":
                agent_name = str(attrs.get(AGENT_NAME, "unknown"))

            # Look for reasoning from sibling or ancestor REASONING spans
            reasoning = self._find_reasoning(
                span, by_id, children, llm_span_id
            )

            decisions.append(
                ToolDecision(
                    tool_name=tool_name,
                    tool_span_id=tool_span_id,
                    llm_span_id=llm_span_id,
                    llm_model=llm_model,
                    agent_name=agent_name,
                    reasoning=reasoning,
                    trace_id=trace_id,
                )
            )

        return decisions

    def _find_reasoning(
        self,
        tool_span: Dict[str, Any],
        by_id: Dict[str, Dict[str, Any]],
        children: Dict[Optional[str], List[str]],
        llm_span_id: str,
    ) -> Optional[str]:
        """Find reasoning text from REASONING spans near the tool call.

        Checks siblings of the tool span first, then siblings of the parent
        LLM_CALL span.
        """
        # Check siblings of the tool span
        parent_id = tool_span.get("parent_span_id")
        reasoning = self._reasoning_from_children(parent_id, by_id, children)
        if reasoning:
            return reasoning

        # Check siblings of the LLM_CALL span
        if llm_span_id:
            llm_span = by_id.get(llm_span_id)
            if llm_span:
                llm_parent = llm_span.get("parent_span_id")
                reasoning = self._reasoning_from_children(
                    llm_parent, by_id, children
                )
                if reasoning:
                    return reasoning

        return None

    @staticmethod
    def _reasoning_from_children(
        parent_id: Optional[str],
        by_id: Dict[str, Dict[str, Any]],
        children: Dict[Optional[str], List[str]],
    ) -> Optional[str]:
        """Extract reasoning text from REASONING children of a given parent."""
        if parent_id is None:
            return None
        for child_id in children.get(parent_id, []):
            child = by_id.get(child_id)
            if child is None:
                continue
            if (child.get("agent_span_kind") or "") == AgentSpanKind.REASONING:
                child_attrs = child.get("attributes") or {}
                chain = child_attrs.get(REASONING_CHAIN)
                if chain:
                    return str(chain)
        return None
