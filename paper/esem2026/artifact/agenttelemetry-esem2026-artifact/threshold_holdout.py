#!/usr/bin/env python3
"""Held-out no-fault validation for the infinite-loop retry threshold."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from compute_roc import DSM_CONDITIONS, THIRD_PARTY, loop_fires


THRESHOLDS = [2, 3, 4, 5, 6]
TRAIN_SCENARIOS = {"writer_repeat", "planning_review", "guardrail_pass"}
HOLDOUT_SCENARIOS = {"simple_success", "retrieval_refresh", "memory_lookup"}


def read_jsonl(path: Path) -> list[dict[str, object]]:
    traces = []
    with path.open() as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
    return traces


def count_control_false_positives(
    traces: list[dict[str, object]],
    scenarios: set[str],
    threshold: int,
) -> tuple[int, int]:
    fp = 0
    fp_n = 0
    for trace in traces:
        if trace["framework"] not in THIRD_PARTY or trace["condition"] not in DSM_CONDITIONS:
            continue
        if trace["fault_type"] != "no_fault" or trace.get("control_scenario") not in scenarios:
            continue
        fp_n += 1
        fp += int(loop_fires(trace["spans"], threshold))
    return fp, fp_n


def count_infinite_loop_true_positives(traces: list[dict[str, object]], threshold: int) -> tuple[int, int]:
    tp = 0
    tp_n = 0
    for trace in traces:
        if trace["framework"] not in THIRD_PARTY or trace["condition"] not in DSM_CONDITIONS:
            continue
        if trace["fault_type"] != "infinite_loop":
            continue
        tp_n += 1
        tp += int(loop_fires(trace["spans"], threshold))
    return tp, tp_n


def evaluate(control_traces: list[dict[str, object]], fault_traces: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for threshold in THRESHOLDS:
        train_fp, train_n = count_control_false_positives(control_traces, TRAIN_SCENARIOS, threshold)
        holdout_fp, holdout_n = count_control_false_positives(control_traces, HOLDOUT_SCENARIOS, threshold)
        tp, tp_n = count_infinite_loop_true_positives(fault_traces, threshold)
        rows.append(
            {
                "max_retries": threshold,
                "train_fp_count": train_fp,
                "train_fp_n": train_n,
                "train_fpr": train_fp / train_n,
                "holdout_fp_count": holdout_fp,
                "holdout_fp_n": holdout_n,
                "holdout_fpr": holdout_fp / holdout_n,
                "tp_count": tp,
                "tp_n": tp_n,
                "tpr": tp / tp_n,
                "selected": 0,
            }
        )

    zero_train_fp = [row for row in rows if row["train_fp_count"] == 0]
    if zero_train_fp:
        selected_threshold = min(int(row["max_retries"]) for row in zero_train_fp)
    else:
        selected_threshold = min(
            rows,
            key=lambda row: (int(row["train_fp_count"]), int(row["max_retries"])),
        )["max_retries"]

    for row in rows:
        row["selected"] = int(row["max_retries"] == selected_threshold)
        row["train_scenarios"] = ",".join(sorted(TRAIN_SCENARIOS))
        row["holdout_scenarios"] = ",".join(sorted(HOLDOUT_SCENARIOS))
    return rows


def write_tsv(rows: list[dict[str, object]], path: Path) -> None:
    fieldnames = [
        "max_retries",
        "train_fp_count",
        "train_fp_n",
        "train_fpr",
        "holdout_fp_count",
        "holdout_fp_n",
        "holdout_fpr",
        "tp_count",
        "tp_n",
        "tpr",
        "selected",
        "train_scenarios",
        "holdout_scenarios",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            formatted = row.copy()
            for key in ["train_fpr", "holdout_fpr", "tpr"]:
                formatted[key] = f"{float(formatted[key]):.3f}"
            writer.writerow(formatted)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", default="no_fault_suite_traces.jsonl")
    parser.add_argument("--faults", default="traces_full.jsonl")
    parser.add_argument("--output", default="threshold_holdout.tsv")
    args = parser.parse_args()
    rows = evaluate(read_jsonl(Path(args.controls)), read_jsonl(Path(args.faults)))
    write_tsv(rows, Path(args.output))
    selected = next(row for row in rows if row["selected"])
    print(f"wrote {args.output}")
    print(
        "selected max_retries="
        f"{selected['max_retries']} "
        f"(train FP {selected['train_fp_count']}/{selected['train_fp_n']}; "
        f"holdout FP {selected['holdout_fp_count']}/{selected['holdout_fp_n']}; "
        f"TP {selected['tp_count']}/{selected['tp_n']})"
    )


if __name__ == "__main__":
    main()
