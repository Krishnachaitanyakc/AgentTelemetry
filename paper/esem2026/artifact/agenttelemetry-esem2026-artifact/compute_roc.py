#!/usr/bin/env python3
"""Threshold sweep for the only non-zero-FPR DSM detector."""

from __future__ import annotations

import csv
import json
from pathlib import Path


THIRD_PARTY = {"anthropic_sdk", "autogen", "crewai", "langchain", "llamaindex", "openai_sdk"}
DSM_CONDITIONS = {"metadata_only", "full_capture"}


def loop_fires(spans: list[dict[str, object]], threshold: int) -> bool:
    counts: dict[str, int] = {}
    for span in spans:
        attrs = span.get("attributes", {})
        if not isinstance(attrs, dict):
            continue
        tool_name = attrs.get("tool.name")
        if isinstance(tool_name, str):
            counts[tool_name] = counts.get(tool_name, 0) + 1
    return any(count >= threshold for count in counts.values())


def recompute_sweep(traces_path: Path) -> list[dict[str, int]]:
    traces = []
    with traces_path.open() as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
    rows = []
    for threshold in [2, 3, 4, 5, 6]:
        fp = fp_n = tp = tp_n = 0
        for trace in traces:
            if trace["framework"] not in THIRD_PARTY or trace["condition"] not in DSM_CONDITIONS:
                continue
            if trace["fault_type"] == "no_fault":
                fp_n += 1
                fp += int(loop_fires(trace["spans"], threshold))
            elif trace["fault_type"] == "infinite_loop":
                tp_n += 1
                tp += int(loop_fires(trace["spans"], threshold))
        rows.append({"max_retries": threshold, "fp_count": fp, "fp_n": fp_n, "tp_count": tp, "tp_n": tp_n})
    return rows


def main() -> None:
    traces_path = Path(__file__).with_name("traces_full.jsonl")
    rows = recompute_sweep(traces_path)
    print("max_retries\tfp_count\tfp_n\tfpr\ttp_count\ttp_n\ttpr")
    for row in rows:
        fp = row["fp_count"]
        fp_n = row["fp_n"]
        tp = row["tp_count"]
        tp_n = row["tp_n"]
        print(f"{row['max_retries']}\t{fp}\t{fp_n}\t{fp/fp_n:.3f}\t{tp}\t{tp_n}\t{tp/tp_n:.3f}")


if __name__ == "__main__":
    main()
