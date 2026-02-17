"""JSON file exporter — writes spans to a JSON Lines file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agenttelemetry.core.trace import AgentSpan


class JSONFileExporter:
    """Exports agent spans to a JSON Lines (.jsonl) file.

    Each span is written as a single JSON object per line, enabling
    efficient streaming reads and integration with log analysis tools.
    """

    def __init__(self, file_path: str = "agent_traces.jsonl"):
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def export_span(self, span: "AgentSpan") -> None:
        with open(self._file_path, "a") as f:
            f.write(json.dumps(span.to_dict(), default=str) + "\n")

    def read_traces(self) -> list:
        """Read all spans from the file, grouped by trace_id."""
        spans = []
        if not self._file_path.exists():
            return spans
        with open(self._file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))
        return spans
