"""Anomaly detection for agent traces.

Implements four detectors:
- Circular delegation (agent A -> B -> A)
- Infinite retries (same tool called repeatedly)
- Cost explosion (total cost exceeding threshold)
- Context overflow (progressive input-token growth across LLM calls)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from agenttelemetry.core.spans import (
    AGENT_NAME,
    AGENT_SPAN_KIND,
    DELEGATION_SOURCE_AGENT,
    DELEGATION_TARGET_AGENT,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    TOOL_INPUT,
    TOOL_NAME,
    AgentSpanKind,
    estimate_cost,
)


class AnomalyType(Enum):
    """Categories of detectable anomalies."""

    CIRCULAR_DELEGATION = "circular_delegation"
    INFINITE_RETRY = "infinite_retry"
    COST_EXPLOSION = "cost_explosion"
    CONTEXT_OVERFLOW = "context_overflow"


@dataclass
class Anomaly:
    """A single detected anomaly."""

    anomaly_type: AnomalyType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    root_span_id: str
    trace_id: str
    details: Dict[str, Any] = field(default_factory=dict)


class AnomalyDetector:
    """Run multiple anomaly detectors over a list of span dicts.

    Args:
        max_retries: Number of identical tool calls to flag as infinite retry.
        cost_threshold: USD threshold above which a trace is flagged.
        token_growth_factor: Multiplicative growth in input tokens between
            consecutive LLM calls that signals context overflow.
    """

    def __init__(
        self,
        max_retries: int = 5,
        cost_threshold: float = 1.0,
        token_growth_factor: float = 2.0,
    ):
        self._max_retries = max_retries
        self._cost_threshold = cost_threshold
        self._token_growth_factor = token_growth_factor

    def detect(self, spans: List[Dict[str, Any]]) -> List[Anomaly]:
        """Run all detectors and return a combined list of anomalies."""
        anomalies: List[Anomaly] = []
        anomalies.extend(self._detect_circular_delegation(spans))
        anomalies.extend(self._detect_infinite_retries(spans))
        anomalies.extend(self._detect_cost_explosion(spans))
        anomalies.extend(self._detect_context_overflow(spans))
        return anomalies

    # ------------------------------------------------------------------
    # Circular delegation
    # ------------------------------------------------------------------

    def _detect_circular_delegation(
        self, spans: List[Dict[str, Any]]
    ) -> List[Anomaly]:
        """Find DELEGATION spans where agent A -> B -> ... -> A."""
        anomalies: List[Anomaly] = []

        # Group delegation spans by trace
        delegations_by_trace: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for span in spans:
            if (span.get("agent_span_kind") or "") == AgentSpanKind.DELEGATION:
                trace_id = span.get("trace_id", "unknown")
                delegations_by_trace[trace_id].append(span)

        for trace_id, deleg_spans in delegations_by_trace.items():
            # Build delegation graph: source -> list of (target, span_id)
            graph: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
            for span in deleg_spans:
                attrs = span.get("attributes") or {}
                source = str(attrs.get(DELEGATION_SOURCE_AGENT, ""))
                target = str(attrs.get(DELEGATION_TARGET_AGENT, ""))
                if source and target:
                    graph[source].append(
                        (target, span.get("span_id", ""))
                    )

            # Detect cycles via DFS
            visited: set = set()
            path: List[str] = []

            def _dfs(node: str) -> Optional[List[str]]:
                if node in path:
                    # Found a cycle
                    cycle_start = path.index(node)
                    return path[cycle_start:] + [node]
                if node in visited:
                    return None
                visited.add(node)
                path.append(node)
                for target, _ in graph.get(node, []):
                    cycle = _dfs(target)
                    if cycle is not None:
                        return cycle
                path.pop()
                return None

            for start_node in graph:
                visited.clear()
                path.clear()
                cycle = _dfs(start_node)
                if cycle is not None:
                    # Find the span_id of the first delegation in the cycle
                    root_span_id = ""
                    for span in deleg_spans:
                        attrs = span.get("attributes") or {}
                        src = str(attrs.get(DELEGATION_SOURCE_AGENT, ""))
                        if src == cycle[0]:
                            root_span_id = span.get("span_id", "")
                            break

                    anomalies.append(
                        Anomaly(
                            anomaly_type=AnomalyType.CIRCULAR_DELEGATION,
                            severity="high",
                            description=(
                                f"Circular delegation detected: "
                                f"{' -> '.join(cycle)}"
                            ),
                            root_span_id=root_span_id,
                            trace_id=trace_id,
                            details={"cycle": cycle},
                        )
                    )
                    break  # One cycle per trace is sufficient

        return anomalies

    # ------------------------------------------------------------------
    # Infinite retries
    # ------------------------------------------------------------------

    def _detect_infinite_retries(
        self, spans: List[Dict[str, Any]]
    ) -> List[Anomaly]:
        """Find same tool called N+ times with same args within a trace."""
        anomalies: List[Anomaly] = []

        # Group tool calls by (trace_id, tool_name, tool_input)
        call_groups: Dict[
            Tuple[str, str, str], List[Dict[str, Any]]
        ] = defaultdict(list)

        for span in spans:
            if (span.get("agent_span_kind") or "") != AgentSpanKind.TOOL_CALL:
                continue
            attrs = span.get("attributes") or {}
            trace_id = span.get("trace_id", "unknown")
            tool_name = str(attrs.get(TOOL_NAME, span.get("name", "")))
            tool_input = str(attrs.get(TOOL_INPUT, ""))
            key = (trace_id, tool_name, tool_input)
            call_groups[key].append(span)

        for (trace_id, tool_name, _), group_spans in call_groups.items():
            if len(group_spans) >= self._max_retries:
                first_span = group_spans[0]
                severity = "high" if len(group_spans) >= self._max_retries * 2 else "medium"
                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.INFINITE_RETRY,
                        severity=severity,
                        description=(
                            f"Tool '{tool_name}' called {len(group_spans)} times "
                            f"with identical arguments in trace {trace_id}"
                        ),
                        root_span_id=first_span.get("span_id", ""),
                        trace_id=trace_id,
                        details={
                            "tool_name": tool_name,
                            "call_count": len(group_spans),
                            "span_ids": [
                                s.get("span_id", "") for s in group_spans
                            ],
                        },
                    )
                )

        return anomalies

    # ------------------------------------------------------------------
    # Cost explosion
    # ------------------------------------------------------------------

    def _detect_cost_explosion(
        self, spans: List[Dict[str, Any]]
    ) -> List[Anomaly]:
        """Flag traces whose total LLM cost exceeds the threshold."""
        anomalies: List[Anomaly] = []

        # Accumulate cost per trace
        trace_costs: Dict[str, float] = defaultdict(float)
        trace_first_span: Dict[str, str] = {}

        for span in spans:
            if (span.get("agent_span_kind") or "") != AgentSpanKind.LLM_CALL:
                continue
            attrs = span.get("attributes") or {}
            trace_id = span.get("trace_id", "unknown")

            cost = attrs.get(LLM_COST)
            if cost is not None and float(cost) > 0:
                trace_costs[trace_id] += float(cost)
            else:
                input_tokens = int(attrs.get(LLM_INPUT_TOKENS, 0) or 0)
                output_tokens = int(attrs.get(LLM_OUTPUT_TOKENS, 0) or 0)
                model = str(attrs.get(LLM_MODEL, ""))
                trace_costs[trace_id] += estimate_cost(
                    model, input_tokens, output_tokens
                )

            if trace_id not in trace_first_span:
                trace_first_span[trace_id] = span.get("span_id", "")

        for trace_id, total_cost in trace_costs.items():
            if total_cost >= self._cost_threshold:
                ratio = total_cost / self._cost_threshold
                if ratio >= 10:
                    severity = "critical"
                elif ratio >= 5:
                    severity = "high"
                elif ratio >= 2:
                    severity = "medium"
                else:
                    severity = "low"

                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.COST_EXPLOSION,
                        severity=severity,
                        description=(
                            f"Trace {trace_id} cost ${total_cost:.4f} "
                            f"exceeds threshold ${self._cost_threshold:.2f}"
                        ),
                        root_span_id=trace_first_span.get(trace_id, ""),
                        trace_id=trace_id,
                        details={
                            "total_cost": total_cost,
                            "threshold": self._cost_threshold,
                        },
                    )
                )

        return anomalies

    # ------------------------------------------------------------------
    # Context overflow
    # ------------------------------------------------------------------

    def _detect_context_overflow(
        self, spans: List[Dict[str, Any]]
    ) -> List[Anomaly]:
        """Detect progressive increase in input tokens across LLM calls."""
        anomalies: List[Anomaly] = []

        # Group LLM_CALL spans by trace, ordered by start time
        llm_by_trace: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for span in spans:
            if (span.get("agent_span_kind") or "") != AgentSpanKind.LLM_CALL:
                continue
            trace_id = span.get("trace_id", "unknown")
            llm_by_trace[trace_id].append(span)

        for trace_id, llm_spans in llm_by_trace.items():
            if len(llm_spans) < 3:
                continue

            # Sort by start time
            llm_spans.sort(key=lambda s: s.get("start_time_ns", 0) or 0)

            token_counts: List[int] = []
            for s in llm_spans:
                attrs = s.get("attributes") or {}
                tokens = int(attrs.get(LLM_INPUT_TOKENS, 0) or 0)
                token_counts.append(tokens)

            # Check for sustained growth: count consecutive increases where
            # the ratio exceeds the growth factor
            growth_streak = 0
            max_streak = 0
            streak_start_idx = 0
            best_start_idx = 0

            for i in range(1, len(token_counts)):
                prev = token_counts[i - 1]
                curr = token_counts[i]
                if prev > 0 and curr >= prev * self._token_growth_factor:
                    if growth_streak == 0:
                        streak_start_idx = i - 1
                    growth_streak += 1
                    if growth_streak > max_streak:
                        max_streak = growth_streak
                        best_start_idx = streak_start_idx
                else:
                    growth_streak = 0

            if max_streak >= 2:
                root_span = llm_spans[best_start_idx]
                severity = "critical" if max_streak >= 4 else "high"
                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.CONTEXT_OVERFLOW,
                        severity=severity,
                        description=(
                            f"Input tokens grew >{self._token_growth_factor}x "
                            f"for {max_streak + 1} consecutive LLM calls "
                            f"in trace {trace_id}"
                        ),
                        root_span_id=root_span.get("span_id", ""),
                        trace_id=trace_id,
                        details={
                            "growth_streak": max_streak,
                            "token_sequence": token_counts[
                                best_start_idx : best_start_idx + max_streak + 2
                            ],
                        },
                    )
                )

        return anomalies
