#!/usr/bin/env python3
"""Aggregate false-positive rates from the per-run TSV."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


THIRD_PARTY = {"anthropic_sdk", "autogen", "crewai", "langchain", "llamaindex", "openai_sdk"}
DSM_CONDITIONS = {"metadata_only", "full_capture"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="?", default="results_full.tsv")
    args = parser.parse_args()

    per_condition = defaultdict(lambda: [0, 0])
    per_adapter_condition = defaultdict(lambda: [0, 0])
    dsm_third_party_by_condition = defaultdict(lambda: [0, 0])
    dsm_third_party = [0, 0]

    with Path(args.results).open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["fault_type"] != "no_fault":
                continue
            detected = int(row["faults_detected"]) > 0
            condition = row["condition"]
            adapter = row["framework"]
            per_condition[condition][1] += 1
            per_adapter_condition[(adapter, condition)][1] += 1
            if detected:
                per_condition[condition][0] += 1
                per_adapter_condition[(adapter, condition)][0] += 1
            if adapter in THIRD_PARTY and condition in DSM_CONDITIONS:
                dsm_third_party[1] += 1
                dsm_third_party_by_condition[condition][1] += 1
                if detected:
                    dsm_third_party[0] += 1
                    dsm_third_party_by_condition[condition][0] += 1

    print("Per-condition aggregate controls")
    print("condition\tfp\ttotal\tfpr")
    for condition in sorted(per_condition):
        fp, total = per_condition[condition]
        print(f"{condition}\t{fp}\t{total}\t{fp/total:.3f}")

    print("\nDSM third-party aggregate across privacy levels")
    fp, total = dsm_third_party
    print(f"metadata_only+full_capture\t{fp}\t{total}\t{fp/total:.3f}")

    print("\nDSM third-party by privacy level")
    print("condition\tfp\ttotal\tfpr")
    for condition in sorted(dsm_third_party_by_condition):
        fp, total = dsm_third_party_by_condition[condition]
        print(f"{condition}\t{fp}\t{total}\t{fp/total:.3f}")

    print("\nFalse-positive cells")
    print("adapter\tcondition\tfp\ttotal\tfpr")
    for (adapter, condition), (fp, total) in sorted(per_adapter_condition.items()):
        if fp:
            print(f"{adapter}\t{condition}\t{fp}\t{total}\t{fp/total:.3f}")


if __name__ == "__main__":
    main()
