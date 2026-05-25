"""Compute False-Positive Rate (FPR) for each (framework, condition) cell
from the per-run TSV. Reproduces the 0.071 figure for DSM rows in the paper.

Usage:
    PYTHONPATH=src:. python benchmarks/compute_fpr.py benchmarks/results_full.tsv
"""
from __future__ import annotations
import csv
import sys
from collections import defaultdict


def main(path: str) -> None:
    fp = defaultdict(lambda: [0, 0])  # (framework, condition) -> [fp, total]
    cond_fp = defaultdict(lambda: [0, 0])  # condition -> [fp, total]
    with open(path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row["fault_type"] != "no_fault":
                continue
            cond = row["condition"]
            fw = row["framework"]
            faults_detected = int(row["faults_detected"])
            fp[(fw, cond)][1] += 1
            cond_fp[cond][1] += 1
            if faults_detected > 0:
                fp[(fw, cond)][0] += 1
                cond_fp[cond][0] += 1

    print("# Per-condition aggregate FPR")
    print(f"{'condition':<20} {'FPR':>8} {'fp':>5} {'total':>6}")
    for cond, (n_fp, n_total) in sorted(cond_fp.items()):
        rate = n_fp / n_total if n_total else 0.0
        print(f"{cond:<20} {rate:>8.4f} {n_fp:>5} {n_total:>6}")

    print()
    print("# Per (framework, condition) FPR (rows with FP only)")
    print(f"{'framework':<15} {'condition':<20} {'FPR':>8} {'fp':>5} {'total':>6}")
    for (fw, cond), (n_fp, n_total) in sorted(fp.items()):
        if n_fp == 0:
            continue
        rate = n_fp / n_total if n_total else 0.0
        print(f"{fw:<15} {cond:<20} {rate:>8.4f} {n_fp:>5} {n_total:>6}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "benchmarks/results_full.tsv")
