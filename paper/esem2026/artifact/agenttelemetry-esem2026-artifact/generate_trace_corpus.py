#!/usr/bin/env python3
"""Generate the deterministic span-trace corpus used by the benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapter_harness import ADAPTERS, CONDITIONS, FAULTS, MODELS, run_adapter_case


def generate(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w") as f:
        for adapter in ADAPTERS:
            for model in MODELS:
                for condition in CONDITIONS:
                    for fault in ["no_fault", *FAULTS]:
                        f.write(json.dumps(run_adapter_case(adapter, model, condition, fault), sort_keys=True) + "\n")
                        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="traces_full.jsonl")
    args = parser.parse_args()
    count = generate(Path(args.output))
    print(f"wrote {args.output}")
    print(f"traces: {count}")


if __name__ == "__main__":
    main()
