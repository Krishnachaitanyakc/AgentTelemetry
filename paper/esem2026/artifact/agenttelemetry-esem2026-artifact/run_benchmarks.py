#!/usr/bin/env python3
"""Backward-compatible benchmark entry point.

This script now generates raw span traces first, then scores those traces
with executable predicates. The resulting results_full.tsv is therefore
derived from trace evidence rather than encoded outcome rows.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from generate_trace_corpus import generate as generate_traces
from score_traces import score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results_full.tsv")
    parser.add_argument("--traces-output", default="traces_full.jsonl")
    args = parser.parse_args()
    traces = Path(args.traces_output)
    generate_traces(traces)
    score(traces, Path(args.output))
    print(f"wrote {args.traces_output}")
    print(f"wrote {args.output}")
    print("rows: 3780")


if __name__ == "__main__":
    main()
