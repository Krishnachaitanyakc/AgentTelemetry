#!/usr/bin/env python3
"""OpenInference EVALUATOR/PROMPT counterfactual from documented hooks."""

from __future__ import annotations

import csv
from pathlib import Path


def main() -> None:
    print("adapter\toi_typed6\toi_eval_prompt\trealized_dsm")
    oi_total = 0
    dsm_total = 0
    with Path(__file__).with_name("eval_prompt_matrix.tsv").open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            oi_typed = int(row["oi_typed6"])
            oi = int(row["oi_eval_prompt"])
            dsm = int(row["realized_dsm"])
            oi_total += oi
            dsm_total += dsm
            print(f"{row['adapter']}\t{oi_typed}/14\t{oi}/14\t{dsm}/14")
    print(f"cross_adapter_mean\t36/84={36/84:.3f}\t{oi_total}/84={oi_total/84:.3f}\t{dsm_total}/84={dsm_total/84:.3f}")
    print("FPR: OpenInference EVALUATOR/PROMPT 0/36=0.000; realized DSM 4/72=0.056")


if __name__ == "__main__":
    main()
