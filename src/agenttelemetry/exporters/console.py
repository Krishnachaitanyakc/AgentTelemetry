"""Console exporter — prints spans to stdout."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agenttelemetry.core.trace import AgentSpan


class ConsoleExporter:
    """Exports agent spans to the console with formatted output."""

    def __init__(self, verbose: bool = False):
        self._verbose = verbose

    def export_span(self, span: "AgentSpan") -> None:
        if self._verbose:
            print(json.dumps(span.to_dict(), indent=2, default=str))
        else:
            status = span.status.value.upper()
            duration = f"{span.duration_ms:.1f}ms"
            parts = [
                f"[{status}]",
                f"{span.kind.value:<12}",
                f"{span.name:<40}",
                f"{duration:>10}",
            ]
            # Add token info for LLM calls
            if span.input_tokens or span.output_tokens:
                tokens = f"{span.input_tokens}→{span.output_tokens} tokens"
                parts.append(tokens)
            if span.cost_usd > 0:
                parts.append(f"${span.cost_usd:.6f}")
            # Add tool info
            if span.tool_name:
                success = span.attributes.get("tool.success", "?")
                parts.append(f"success={success}")

            print(" | ".join(parts))
