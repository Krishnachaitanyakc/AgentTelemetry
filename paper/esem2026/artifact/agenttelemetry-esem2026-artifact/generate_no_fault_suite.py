#!/usr/bin/env python3
"""Generate the supplemental multi-workflow no-fault control suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapter_harness import ADAPTERS, CONDITIONS, MODELS, NO_FAULT_SCENARIOS, run_adapter_case


def generate(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w") as f:
        for scenario in NO_FAULT_SCENARIOS:
            for adapter in ADAPTERS:
                for model in MODELS:
                    for condition in CONDITIONS:
                        trace = run_adapter_case(adapter, model, condition, "no_fault", scenario)
                        f.write(json.dumps(trace, sort_keys=True) + "\n")
                        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="no_fault_suite_traces.jsonl")
    args = parser.parse_args()
    count = generate(Path(args.output))
    print(f"wrote {args.output}")
    print(f"traces: {count}")


if __name__ == "__main__":
    main()
