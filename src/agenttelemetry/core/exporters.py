"""Custom exporters for AgentTelemetry.

Provides agent-aware console and JSON exporters that understand
agent span kinds and render trace trees.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agenttelemetry.core.spans import AGENT_SPAN_KIND, LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS, LLM_COST, TOOL_NAME


def _span_to_dict(span: ReadableSpan) -> Dict[str, Any]:
    """Convert an OTel ReadableSpan to a JSON-serializable dict."""
    parent_id = None
    if span.parent is not None:
        parent_id = format(span.parent.span_id, "016x")

    return {
        "trace_id": format(span.context.trace_id, "032x"),
        "span_id": format(span.context.span_id, "016x"),
        "parent_span_id": parent_id,
        "name": span.name,
        "kind": span.kind.name if span.kind else "INTERNAL",
        "agent_span_kind": span.attributes.get(AGENT_SPAN_KIND, "") if span.attributes else "",
        "start_time_ns": span.start_time,
        "end_time_ns": span.end_time,
        "duration_ms": (span.end_time - span.start_time) / 1_000_000 if span.end_time and span.start_time else 0,
        "status": {
            "code": span.status.status_code.name if span.status else "UNSET",
            "description": span.status.description if span.status else "",
        },
        "attributes": dict(span.attributes) if span.attributes else {},
        "events": [
            {
                "name": e.name,
                "timestamp": e.timestamp,
                "attributes": dict(e.attributes) if e.attributes else {},
            }
            for e in (span.events or [])
        ],
        "resource": dict(span.resource.attributes) if span.resource else {},
    }


class AgentTelemetryConsoleExporter(SpanExporter):
    """Pretty-prints agent trace trees to console."""

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            if self._verbose:
                print(json.dumps(_span_to_dict(span), indent=2, default=str))
            else:
                attrs = span.attributes or {}
                agent_kind = attrs.get(AGENT_SPAN_KIND, "INTERNAL")
                status = span.status.status_code.name if span.status else "UNSET"
                duration_ms = (span.end_time - span.start_time) / 1_000_000 if span.end_time and span.start_time else 0

                parts = [
                    f"[{status}]",
                    f"{agent_kind:<12}",
                    f"{span.name:<40}",
                    f"{duration_ms:>10.1f}ms",
                ]

                input_tokens = attrs.get(LLM_INPUT_TOKENS, 0)
                output_tokens = attrs.get(LLM_OUTPUT_TOKENS, 0)
                if input_tokens or output_tokens:
                    parts.append(f"{input_tokens}\u2192{output_tokens} tokens")

                cost = attrs.get(LLM_COST, 0)
                if cost and cost > 0:
                    parts.append(f"${cost:.6f}")

                tool = attrs.get(TOOL_NAME)
                if tool:
                    parts.append(f"tool={tool}")

                print(" | ".join(parts))

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class AgentTelemetryJSONExporter(SpanExporter):
    """Writes agent traces to a JSON Lines file for analysis."""

    def __init__(self, file_path: str = "agent_traces.jsonl") -> None:
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._spans: List[Dict[str, Any]] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            with open(self._file_path, "a") as f:
                for span in spans:
                    d = _span_to_dict(span)
                    self._spans.append(d)
                    f.write(json.dumps(d, default=str) + "\n")
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE

    def get_exported_spans(self) -> List[Dict[str, Any]]:
        """Return all spans exported so far (in-memory)."""
        return list(self._spans)

    def read_traces(self) -> List[Dict[str, Any]]:
        """Read all spans from the file."""
        spans = []
        if not self._file_path.exists():
            return spans
        with open(self._file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))
        return spans

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
