"""Cost aggregation across agent traces.

Walks LLM_CALL spans, sums token counts and costs, and groups results
by model, agent, and trace.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agenttelemetry.core.spans import (
    AGENT_NAME,
    AGENT_SPAN_KIND,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    MODEL_COSTS,
    AgentSpanKind,
    estimate_cost,
)


@dataclass
class ModelCost:
    """Aggregated cost data for a single model."""

    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 0


@dataclass
class CostReport:
    """Complete cost breakdown for a set of traces."""

    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    by_model: Dict[str, ModelCost] = field(default_factory=dict)
    by_agent: Dict[str, float] = field(default_factory=dict)
    by_trace: Dict[str, float] = field(default_factory=dict)


class CostAggregator:
    """Aggregate LLM costs from exported span dicts.

    Args:
        model_costs: Optional override for model pricing. If not provided,
            uses ``MODEL_COSTS`` from ``agenttelemetry.core.spans``.
    """

    def __init__(self, model_costs: Optional[Dict[str, Dict[str, float]]] = None):
        self._model_costs = model_costs if model_costs is not None else MODEL_COSTS

    def analyze(self, spans: List[Dict[str, Any]]) -> CostReport:
        """Produce a :class:`CostReport` from a list of span dicts."""
        report = CostReport()

        for span in spans:
            kind = span.get("agent_span_kind") or ""
            if kind != AgentSpanKind.LLM_CALL:
                continue

            attrs = span.get("attributes") or {}
            input_tokens = int(attrs.get(LLM_INPUT_TOKENS, 0) or 0)
            output_tokens = int(attrs.get(LLM_OUTPUT_TOKENS, 0) or 0)
            model = str(attrs.get(LLM_MODEL, "unknown"))
            agent_name = str(attrs.get(AGENT_NAME, "unknown"))
            trace_id = span.get("trace_id", "unknown")

            # Use explicit cost if present, otherwise estimate
            cost = attrs.get(LLM_COST)
            if cost is not None and float(cost) > 0:
                cost = float(cost)
            else:
                cost = self._estimate_cost(model, input_tokens, output_tokens)

            # Totals
            report.total_cost += cost
            report.total_input_tokens += input_tokens
            report.total_output_tokens += output_tokens

            # By model
            if model not in report.by_model:
                report.by_model[model] = ModelCost()
            mc = report.by_model[model]
            mc.cost += cost
            mc.input_tokens += input_tokens
            mc.output_tokens += output_tokens
            mc.call_count += 1

            # By agent
            report.by_agent[agent_name] = report.by_agent.get(agent_name, 0.0) + cost

            # By trace
            report.by_trace[trace_id] = report.by_trace.get(trace_id, 0.0) + cost

        return report

    def _estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost from model pricing table."""
        model_key = model.lower().strip()
        for known_model, costs in self._model_costs.items():
            if known_model in model_key:
                return (
                    input_tokens * costs["input"] / 1_000_000
                    + output_tokens * costs["output"] / 1_000_000
                )
        return 0.0
