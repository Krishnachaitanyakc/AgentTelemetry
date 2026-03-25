"""Model configurations and budget tracking for real LLM experiment."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""

    model_id: str
    display_name: str
    provider: str  # "openai" or "anthropic"
    is_reasoning: bool = False
    cost_input_per_1m: float = 0.0  # USD per 1M input tokens
    cost_output_per_1m: float = 0.0  # USD per 1M output tokens
    max_output_tokens: int = 4096


# ---------------------------------------------------------------------------
# 13 model configs: 7 OpenAI + 6 Anthropic
# ---------------------------------------------------------------------------

MODELS: Dict[str, ModelConfig] = {
    # OpenAI models
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider="openai",
        cost_input_per_1m=0.15,
        cost_output_per_1m=0.60,
    ),
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        display_name="GPT-4o",
        provider="openai",
        cost_input_per_1m=2.50,
        cost_output_per_1m=10.00,
    ),
    "gpt-4.1-nano": ModelConfig(
        model_id="gpt-4.1-nano",
        display_name="GPT-4.1 Nano",
        provider="openai",
        cost_input_per_1m=0.10,
        cost_output_per_1m=0.40,
    ),
    "gpt-4.1-mini": ModelConfig(
        model_id="gpt-4.1-mini",
        display_name="GPT-4.1 Mini",
        provider="openai",
        cost_input_per_1m=0.40,
        cost_output_per_1m=1.60,
    ),
    "gpt-4.1": ModelConfig(
        model_id="gpt-4.1",
        display_name="GPT-4.1",
        provider="openai",
        cost_input_per_1m=2.00,
        cost_output_per_1m=8.00,
    ),
    "o3-mini": ModelConfig(
        model_id="o3-mini",
        display_name="O3 Mini",
        provider="openai",
        is_reasoning=True,
        cost_input_per_1m=1.10,
        cost_output_per_1m=4.40,
    ),
    "o4-mini": ModelConfig(
        model_id="o4-mini",
        display_name="O4 Mini",
        provider="openai",
        is_reasoning=True,
        cost_input_per_1m=1.10,
        cost_output_per_1m=4.40,
    ),
    # Anthropic models
    "claude-haiku-4-5": ModelConfig(
        model_id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5",
        provider="anthropic",
        cost_input_per_1m=1.00,
        cost_output_per_1m=5.00,
    ),
    "claude-sonnet-4-5": ModelConfig(
        model_id="claude-sonnet-4-5-20250514",
        display_name="Claude Sonnet 4.5",
        provider="anthropic",
        cost_input_per_1m=3.00,
        cost_output_per_1m=15.00,
    ),
    "claude-sonnet-4-6": ModelConfig(
        model_id="claude-sonnet-4-6-20250624",
        display_name="Claude Sonnet 4.6",
        provider="anthropic",
        cost_input_per_1m=3.00,
        cost_output_per_1m=15.00,
    ),
    "claude-opus-4-5": ModelConfig(
        model_id="claude-opus-4-5-20250514",
        display_name="Claude Opus 4.5",
        provider="anthropic",
        cost_input_per_1m=5.00,
        cost_output_per_1m=25.00,
    ),
    "claude-opus-4-6": ModelConfig(
        model_id="claude-opus-4-6-20250624",
        display_name="Claude Opus 4.6",
        provider="anthropic",
        cost_input_per_1m=5.00,
        cost_output_per_1m=25.00,
    ),
    "claude-3-5-sonnet": ModelConfig(
        model_id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        provider="anthropic",
        cost_input_per_1m=3.00,
        cost_output_per_1m=15.00,
    ),
}


def create_client(config: ModelConfig) -> Any:
    """Create an API client for the given model config."""
    if config.provider == "openai":
        from openai import OpenAI

        return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    elif config.provider == "anthropic":
        import anthropic

        return anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            base_url="https://api.anthropic.com",
        )
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


class BudgetTracker:
    """Track API spending with hard stops."""

    def __init__(self, total_budget: float = 14.0, per_model_cap: float = 3.0):
        self.total_budget = total_budget
        self.per_model_cap = per_model_cap
        self.total_spent: float = 0.0
        self.by_model: Dict[str, float] = {}
        self._calls: int = 0

    def record(self, model: str, input_tokens: int, output_tokens: int, config: ModelConfig) -> float:
        """Record a call's cost. Returns cost. Raises if budget exceeded."""
        cost = (
            input_tokens * config.cost_input_per_1m / 1_000_000
            + output_tokens * config.cost_output_per_1m / 1_000_000
        )
        self.total_spent += cost
        self.by_model[model] = self.by_model.get(model, 0.0) + cost
        self._calls += 1

        if self.total_spent > self.total_budget:
            raise RuntimeError(
                f"Budget exceeded: ${self.total_spent:.4f} > ${self.total_budget:.2f}"
            )
        if self.by_model[model] > self.per_model_cap:
            raise RuntimeError(
                f"Per-model cap exceeded for {model}: "
                f"${self.by_model[model]:.4f} > ${self.per_model_cap:.2f}"
            )
        return cost

    def can_afford(self, model: str, estimated_cost: float = 0.01) -> bool:
        """Check if we can afford another call."""
        if self.total_spent + estimated_cost > self.total_budget:
            return False
        if self.by_model.get(model, 0.0) + estimated_cost > self.per_model_cap:
            return False
        return True

    def summary(self) -> str:
        lines = [f"Total: ${self.total_spent:.4f} / ${self.total_budget:.2f} ({self._calls} calls)"]
        for model, cost in sorted(self.by_model.items()):
            lines.append(f"  {model}: ${cost:.4f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Unified response wrapper
# ---------------------------------------------------------------------------

@dataclass
class UnifiedResponse:
    """Normalized response from any LLM provider."""

    content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    tool_calls: list = field(default_factory=list)
    stop_reason: str = ""
    model: str = ""
    raw: Any = None

    @classmethod
    def from_openai(cls, response: Any) -> "UnifiedResponse":
        """Create from OpenAI ChatCompletion response."""
        choice = response.choices[0]
        message = choice.message
        usage = response.usage

        tool_calls = []
        if message.tool_calls:
            import json
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {},
                })

        reasoning_tokens = 0
        if hasattr(usage, "completion_tokens_details") and usage.completion_tokens_details:
            reasoning_tokens = getattr(usage.completion_tokens_details, "reasoning_tokens", 0) or 0

        return cls(
            content=message.content or "",
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            reasoning_tokens=reasoning_tokens,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason or "",
            model=response.model,
            raw=response,
        )

    @classmethod
    def from_anthropic(cls, response: Any) -> "UnifiedResponse":
        """Create from Anthropic Message response."""
        import json

        content_text = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input if isinstance(block.input, dict) else json.loads(block.input),
                })

        return cls(
            content=content_text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            reasoning_tokens=0,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "",
            model=response.model,
            raw=response,
        )
