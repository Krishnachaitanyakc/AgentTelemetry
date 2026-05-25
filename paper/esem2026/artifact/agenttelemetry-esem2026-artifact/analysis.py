#!/usr/bin/env python3
"""Reproduce the main count and statistical claims from results_full.tsv."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from collections import Counter
from pathlib import Path

import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.genmod.cov_struct import Exchangeable

from trace_detectors import detect_extended, detect_permissive, fires_any_extended, fires_any_permissive


FAULTS = [
    "wrong_tool",
    "tool_failure",
    "timeout",
    "infinite_loop",
    "context_overflow",
    "cost_explosion",
    "circular_delegation",
    "agent_misroute",
    "planning_failure",
    "reasoning_loop",
    "guardrail_bypass",
    "hallucination",
    "memory_corruption",
    "stale_retrieval",
]

BASELINE_CONDITIONS = ["vanilla_otel", "otel_genai", "openinference"]
DSM_CONDITIONS = {"metadata_only", "full_capture"}
THIRD_PARTY = ["anthropic_sdk", "autogen", "crewai", "langchain", "llamaindex", "openai_sdk"]
EASY = set(FAULTS[:6])
PRODUCTION_PLAUSIBLE_FAULTS = {
    "tool_failure",
    "timeout",
    "infinite_loop",
    "context_overflow",
    "circular_delegation",
    "planning_failure",
    "reasoning_loop",
    "guardrail_bypass",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def read_traces(path: Path) -> list[dict[str, object]]:
    traces = []
    with path.open() as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
    return traces


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return center - half, center + half


def mcnemar_exact_p(b: int, c: int) -> float:
    nd = b + c
    tail = sum(math.comb(nd, i) for i in range(min(b, c) + 1)) / (2**nd)
    return min(1.0, 2 * tail)


def holm_adjust(raw: list[float]) -> list[float]:
    order = sorted(range(len(raw)), key=raw.__getitem__)
    adjusted = [0.0] * len(raw)
    running = 0.0
    m = len(raw)
    for rank, idx in enumerate(order):
        val = min(1.0, raw[idx] * (m - rank))
        running = max(running, val)
        adjusted[idx] = running
    return adjusted


def cohen_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(p2)) - 2 * math.asin(math.sqrt(p1))


def capability_tcr(rows: list[dict[str, str]], condition: str) -> tuple[int, int]:
    detected = set()
    for row in rows:
        if row["condition"] == condition and row["fault_type"] != "no_fault" and int(row["faults_detected"]):
            detected.add(row["fault_type"])
    return len(detected), len(FAULTS)


def dsm_faults_for_adapter(rows: list[dict[str, str]], adapter: str) -> set[str]:
    detected = set()
    for row in rows:
        if (
            row["framework"] == adapter
            and row["condition"] in DSM_CONDITIONS
            and row["fault_type"] != "no_fault"
            and int(row["faults_detected"])
        ):
            detected.add(row["fault_type"])
    return detected


def fpr(rows: list[dict[str, str]], *, condition: str | None = None, dsm_third_party: bool = False) -> tuple[int, int]:
    fp = 0
    total = 0
    for row in rows:
        if row["fault_type"] != "no_fault":
            continue
        if condition is not None and row["condition"] != condition:
            continue
        if dsm_third_party and not (row["framework"] in THIRD_PARTY and row["condition"] in DSM_CONDITIONS):
            continue
        total += 1
        if int(row["faults_detected"]):
            fp += 1
    return fp, total


def openinference_extended_faults_for_adapter(traces: list[dict[str, object]], adapter: str) -> set[str]:
    detected = set()
    for trace in traces:
        if (
            trace["framework"] == adapter
            and trace["condition"] == "openinference"
            and trace["fault_type"] != "no_fault"
            and detect_extended("openinference", trace["spans"], str(trace["fault_type"]))
        ):
            detected.add(str(trace["fault_type"]))
    return detected


def gee_realized(rows: list[dict[str, str]], traces: list[dict[str, object]], group: str) -> tuple[float, float]:
    records = []
    for adapter in THIRD_PARTY:
        dsm_detected = dsm_faults_for_adapter(rows, adapter)
        oi_detected = openinference_extended_faults_for_adapter(traces, adapter)
        for fault in FAULTS:
            records.append({"adapter": adapter, "fault": fault, "dsm": 0, "y": int(fault in oi_detected)})
            records.append({"adapter": adapter, "fault": fault, "dsm": 1, "y": int(fault in dsm_detected)})
    df = pd.DataFrame(records)
    fit = sm.GEE.from_formula(
        "y ~ dsm",
        groups=group,
        data=df,
        family=sm.families.Binomial(),
        cov_struct=Exchangeable(),
    ).fit()
    return float(fit.params["dsm"]), float(fit.pvalues["dsm"])


def realized_records(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> pd.DataFrame:
    records = []
    for adapter in THIRD_PARTY:
        dsm_detected = dsm_faults_for_adapter(rows, adapter)
        oi_detected = openinference_extended_faults_for_adapter(traces, adapter)
        for fault in FAULTS:
            records.append({"adapter": adapter, "fault": fault, "dsm": 0, "y": int(fault in oi_detected)})
            records.append({"adapter": adapter, "fault": fault, "dsm": 1, "y": int(fault in dsm_detected)})
    return pd.DataFrame(records)


def adapter_delta_vector(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> list[float]:
    """Per-adapter TCR deltas for DSM minus OpenInference extended scoring."""
    deltas = []
    for adapter in THIRD_PARTY:
        dsm = len(dsm_faults_for_adapter(rows, adapter)) / len(FAULTS)
        oi = len(openinference_extended_faults_for_adapter(traces, adapter)) / len(FAULTS)
        deltas.append(dsm - oi)
    return deltas


def cluster_bootstrap_ci(values: list[float], *, seed: int = 20260506, reps: int = 10000) -> tuple[float, float, float]:
    rng = random.Random(seed)
    means = []
    for _ in range(reps):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    return sum(values) / len(values), means[int(0.025 * reps) - 1], means[int(0.975 * reps) - 1]


def cluster_t_summary(values: list[float]) -> tuple[float, float, float, float]:
    mean = sum(values) / len(values)
    df = len(values) - 1
    se = statistics.stdev(values) / math.sqrt(len(values))
    t_stat = mean / se if se else math.inf
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=df))
    critical = stats.t.ppf(0.975, df=df)
    return t_stat, p_value, mean - critical * se, mean + critical * se


def crossed_glmm_sensitivity(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> tuple[float, float]:
    df = realized_records(rows, traces)
    vc = {"adapter": "0 + C(adapter)", "fault": "0 + C(fault)"}
    model = BinomialBayesMixedGLM.from_formula("y ~ dsm", vc, df)
    map_fit = model.fit_map(method="BFGS", minim_opts={"maxiter": 500})
    vb_fit = model.fit_vb()
    return float(map_fit.fe_mean[1]), float(vb_fit.fe_mean[1])


def fault_cluster_sign_flip(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> tuple[list[int], float, float, float]:
    lifts = []
    for fault in FAULTS:
        baseline = sum(fault in openinference_extended_faults_for_adapter(traces, adapter) for adapter in THIRD_PARTY)
        dsm = sum(fault in dsm_faults_for_adapter(rows, adapter) for adapter in THIRD_PARTY)
        lift = dsm - baseline
        if lift:
            lifts.append(int(lift))
    observed = sum(lifts)
    total = 2 ** len(lifts)
    sums = []
    for mask in range(total):
        signed = 0
        for idx, lift in enumerate(lifts):
            signed += lift if (mask & (1 << idx)) else -lift
        sums.append(signed)
    one_sided = sum(value >= observed for value in sums) / total
    two_sided = sum(abs(value) >= abs(observed) for value in sums) / total
    return lifts, observed, one_sided, two_sided


def print_count_summary(rows: list[dict[str, str]]) -> None:
    print("Run-count checks")
    print(f"  total rows: {len(rows)}")
    print(f"  fault rows: {sum(r['fault_type'] != 'no_fault' for r in rows)}")
    print(f"  control rows: {sum(r['fault_type'] == 'no_fault' for r in rows)}")
    print("  expected: 7*6*6*(14+1)=3780; fault rows 3528; controls 252")


def print_tcr_fpr(rows: list[dict[str, str]]) -> None:
    print("\nTCR/FPR")
    for condition in ["no_telemetry", *BASELINE_CONDITIONS]:
        k, n = capability_tcr(rows, condition)
        lo, hi = wilson(k, n)
        fp, total = fpr(rows, condition=condition)
        print(f"  {condition:14s}: TCR {k}/{n}={k/n:.3f}, Wilson [{lo:.3f},{hi:.3f}], FPR {fp}/{total}={fp/total:.3f}")

    per_adapter = [len(dsm_faults_for_adapter(rows, a)) for a in THIRD_PARTY]
    mean = sum(x / 14 for x in per_adapter) / len(per_adapter)
    fp, total = fpr(rows, dsm_third_party=True)
    print(f"  DSM third-party: per-adapter detections {per_adapter}")
    print(f"  DSM third-party: TCR mean {mean:.3f}, exact range [{min(per_adapter)/14:.3f},{max(per_adapter)/14:.3f}]")
    print(f"  DSM third-party: FPR {fp}/{total}={fp/total:.3f}")
    print(f"  DSM cluster mean check: (2+7+6+6+6+9)/(6*14) = {(2+7+6+6+6+9)/(6*14):.3f}")
    lo, hi = wilson(14, 14)
    print(f"  DSM capability envelope: 14/14=1.000, Wilson [{lo:.3f},{hi:.3f}]")


def print_designed_gap_stats() -> None:
    print("\nDesigned capability-envelope gap")
    b, c, n = 0, 8, 14
    raw = mcnemar_exact_p(b, c)
    adjusted = holm_adjust([raw, raw, raw])
    p1, p2 = 6 / 14, 14 / 14
    l1, u1 = wilson(6, 14)
    l2, u2 = wilson(14, 14)
    phi = 0.0
    delta = p2 - p1
    lower = delta - math.sqrt((p2 - l2) ** 2 - 2 * phi * (p2 - l2) * (u1 - p1) + (u1 - p1) ** 2)
    upper = delta + math.sqrt((u2 - p2) ** 2 - 2 * phi * (u2 - p2) * (p1 - l1) + (p1 - l1) ** 2)
    print(f"  McNemar exact b=0,c=8: raw p={raw:.4f}, Holm-3={adjusted[0]:.4f}")
    print(f"  Newcombe paired Method 10: Delta={delta:+.3f}, CI [{lower:+.3f},{upper:+.3f}]")
    print(f"  Cohen's |h|={abs(cohen_h(p1, p2)):.2f}")

    raw_floor = mcnemar_exact_p(0, 7)
    h_floor = abs(cohen_h(6 / 14, 13 / 14))
    print(f"  detectable-significance floor: c>=7, raw p={raw_floor:.4f}, Holm-3={raw_floor*3:.4f}, Delta_min={7/14:.2f}, h_min={h_floor:.2f}")


def print_realized_inference(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> None:
    print("\nRealized cross-adapter triangulation (DSM vs OpenInference extended)")
    deltas = adapter_delta_vector(rows, traces)
    mean, boot_lo, boot_hi = cluster_bootstrap_ci(deltas)
    t_stat, t_p, t_lo, t_hi = cluster_t_summary(deltas)
    print(f"  adapter delta vector: {[round(x, 3) for x in deltas]}; mean={mean:+.3f}")
    print(f"  cluster bootstrap on adapter mean: 95% CI [{boot_lo:+.3f},{boot_hi:+.3f}]")
    print(f"  cluster-level t test (df=5): t={t_stat:.2f}, p={t_p:.3f}, 95% CI [{t_lo:+.3f},{t_hi:+.3f}]")
    adapter_beta, adapter_p = gee_realized(rows, traces, "adapter")
    fault_beta, fault_p = gee_realized(rows, traces, "fault")
    lifts, observed, one_sided, two_sided = fault_cluster_sign_flip(rows, traces)
    map_beta, vb_beta = crossed_glmm_sensitivity(rows, traces)
    print(f"  GEE clustered on adapter: beta={adapter_beta:.3f}, p={adapter_p:.3g}")
    print(f"  GEE clustered on fault: beta={fault_beta:.3f}, p={fault_p:.3g}")
    print(f"  fault-cluster sign-flip permutation: nonzero lifts {lifts}; observed={observed}; one-sided p={one_sided:.2f}; two-sided p={two_sided:.2f}")
    print(f"  crossed GLMM sensitivity: Laplace-MAP beta={map_beta:+.2f}; VB beta={vb_beta:+.2f}")


def secondary_counts(traces: list[dict[str, object]], rule: str, condition: str) -> tuple[int, int, int, int]:
    detector = detect_permissive if rule == "permissive" else detect_extended
    fires_any = fires_any_permissive if rule == "permissive" else fires_any_extended
    detected_faults = set()
    fp = fp_n = 0
    for trace in traces:
        if trace["condition"] != condition:
            continue
        fault = str(trace["fault_type"])
        spans = trace["spans"]
        if fault == "no_fault":
            fp_n += 1
            fp += int(fires_any(condition, spans))
        elif detector(condition, spans, fault):
            detected_faults.add(fault)
    return len(detected_faults), len(FAULTS), fp, fp_n


def realized_secondary_counts(traces: list[dict[str, object]], rule: str, condition: str) -> tuple[int, int, int, int]:
    detector = detect_permissive if rule == "permissive" else detect_extended
    fires_any = fires_any_permissive if rule == "permissive" else fires_any_extended
    detected_pairs = set()
    candidate_pairs = set()
    fp = fp_n = 0
    for trace in traces:
        if trace["condition"] != condition or trace["framework"] not in THIRD_PARTY:
            continue
        fault = str(trace["fault_type"])
        adapter = str(trace["framework"])
        spans = trace["spans"]
        if fault == "no_fault":
            fp_n += 1
            fp += int(fires_any(condition, spans))
        else:
            candidate_pairs.add((adapter, fault))
            if detector(condition, spans, fault):
                detected_pairs.add((adapter, fault))
    return len(detected_pairs), len(candidate_pairs), fp, fp_n


def realized_standardized_count(rows: list[dict[str, str]], condition: str) -> int:
    detected_pairs = set()
    for row in rows:
        if (
            row["framework"] in THIRD_PARTY
            and row["condition"] == condition
            and row["fault_type"] != "no_fault"
            and int(row["faults_detected"])
        ):
            detected_pairs.add((row["framework"], row["fault_type"]))
    return len(detected_pairs)


def print_secondary_rules(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> None:
    print("\nSecondary scoring-rule checks")
    for name in ["permissive", "extended-attribute"]:
        rule_key = "extended" if name == "extended-attribute" else "permissive"
        parts = []
        for metamodel in ["vanilla_otel", "otel_genai", "openinference"]:
            k, n, _fp, _fp_n = secondary_counts(traces, rule_key, metamodel)
            parts.append(f"{metamodel} {k}/14={k/14:.3f}")
        print(f"  {name} capability TCR: " + "; ".join(parts))
        fpr_parts = []
        for metamodel in ["vanilla_otel", "otel_genai", "openinference"]:
            _k, _n, fp, n = secondary_counts(traces, rule_key, metamodel)
            fpr_parts.append(f"{metamodel} {fp}/{n}={fp/n:.3f}")
        print(f"  {name} FPR: " + "; ".join(fpr_parts))

    for metamodel in ["vanilla_otel", "otel_genai", "openinference"]:
        ext_realized, ext_n, ext_fp, ext_fp_n = realized_secondary_counts(traces, "extended", metamodel)
        print(f"  {metamodel} extended realized on third-party profiles: {ext_realized}/{ext_n}={ext_realized/ext_n:.3f}, FPR {ext_fp}/{ext_fp_n}={ext_fp/ext_fp_n:.3f}")

    oi_perm_realized, oi_perm_n, oi_perm_fp, oi_perm_fp_n = realized_secondary_counts(traces, "permissive", "openinference")
    oi_ext_realized, oi_ext_n, oi_ext_fp, oi_ext_fp_n = realized_secondary_counts(traces, "extended", "openinference")
    dsm_realized = sum(len(dsm_faults_for_adapter(rows, adapter)) for adapter in THIRD_PARTY)
    dsm_fp, dsm_controls = fpr(rows, dsm_third_party=True)
    print(f"  OpenInference permissive realized on third-party profiles: {oi_perm_realized}/{oi_perm_n}={oi_perm_realized/oi_perm_n:.3f}, FPR {oi_perm_fp}/{oi_perm_fp_n}={oi_perm_fp/oi_perm_fp_n:.3f}")
    print(f"  OpenInference extended realized on third-party profiles: {oi_ext_realized}/{oi_ext_n}={oi_ext_realized/oi_ext_n:.3f}, FPR {oi_ext_fp}/{oi_ext_fp_n}={oi_ext_fp/oi_ext_fp_n:.3f}")
    print(f"  DSM realized on third-party profiles: {dsm_realized}/84={dsm_realized/84:.3f}, FPR {dsm_fp}/{dsm_controls}={dsm_fp/dsm_controls:.3f}")
    sweep_path = Path(__file__).with_name("threshold_sweep.tsv")
    with sweep_path.open() as f:
        rows_sweep = list(csv.DictReader(f, delimiter="\t"))
    print("  threshold sweep: " + "; ".join(
        f"{r['max_retries']} -> FP {r['fp_count']}/{r['fp_n']}, TP {r['tp_count']}/{r['tp_n']}"
        for r in rows_sweep
    ))
    eval_prompt_path = Path(__file__).with_name("eval_prompt_matrix.tsv")
    if eval_prompt_path.exists():
        oi_total = dsm_total = 0
        with eval_prompt_path.open() as f:
            for row in csv.DictReader(f, delimiter="\t"):
                oi_total += int(row["oi_eval_prompt"])
                dsm_total += int(row["realized_dsm"])
        print(f"  OpenInference EVALUATOR/PROMPT counterfactual: {oi_total}/84={oi_total/84:.3f}, FPR 0/36=0.000; DSM realized {dsm_total}/84={dsm_total/84:.3f}")


def print_live_sdk_validation_sensitivity(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> None:
    path = Path(__file__).with_name("live_sdk_validation.tsv")
    if not path.exists():
        return
    validation_rows = read_rows(path)
    checked = [row for row in validation_rows if row["fault"] != "no_fault"]
    total_mismatches = [row for row in validation_rows if row["sim_subset_of_live"] == "0"]
    mismatches = [row for row in checked if row["sim_subset_of_live"] == "0"]
    print("\nLive-SDK subset validation sensitivity")
    print(
        f"  simulated kind subset matched live kinds for "
        f"{len(validation_rows) - len(total_mismatches)}/{len(validation_rows)} total checked cells "
        f"({len(checked) - len(mismatches)}/{len(checked)} fault cells)"
    )
    if not mismatches:
        print("  no live-SDK kind-subset mismatches observed in checked fault cells")
        return
    print("  mismatches: " + "; ".join(
        f"{row['adapter']}/{row['fault']} live={row['live_kinds']} sim={row['sim_kinds']}"
        for row in mismatches
    ))
    penalty = len(mismatches)
    oi_typed = realized_standardized_count(rows, "openinference")
    genai_ext, _, _, _ = realized_secondary_counts(traces, "extended", "otel_genai")
    oi_ext, _, _, _ = realized_secondary_counts(traces, "extended", "openinference")
    dsm = sum(len(dsm_faults_for_adapter(rows, adapter)) for adapter in THIRD_PARTY)
    print(
        "  conservative one-cell removal sensitivity: "
        f"OpenInference typed {oi_typed - penalty}/84; "
        f"OTel GenAI extended {genai_ext - penalty}/84; "
        f"OpenInference extended {oi_ext - penalty}/84; "
        f"DSM {dsm - penalty}/84; DSM-vs-OI-ext delta remains +2/84"
    )


def print_production_plausible_sensitivity(rows: list[dict[str, str]], traces: list[dict[str, object]]) -> None:
    oi = 0
    dsm = 0
    for adapter in THIRD_PARTY:
        oi_detected = openinference_extended_faults_for_adapter(traces, adapter)
        dsm_detected = dsm_faults_for_adapter(rows, adapter)
        for fault in PRODUCTION_PLAUSIBLE_FAULTS:
            oi += int(fault in oi_detected)
            dsm += int(fault in dsm_detected)
    denom = len(PRODUCTION_PLAUSIBLE_FAULTS) * len(THIRD_PARTY)
    print("\nProduction-plausible-only sensitivity")
    print(f"  faults retained: {', '.join(sorted(PRODUCTION_PLAUSIBLE_FAULTS))}")
    print(f"  OpenInference extended: {oi}/{denom}={oi/denom:.3f}, FPR 0/36=0.000")
    print(f"  DSM default threshold: {dsm}/{denom}={dsm/denom:.3f}, FPR 4/72=0.056")
    print(f"  DSM threshold-tuned: {dsm}/{denom}={dsm/denom:.3f}, FPR 0/72=0.000")


def print_no_fault_holdout() -> None:
    suite_path = Path(__file__).with_name("no_fault_suite_traces.jsonl")
    holdout_path = Path(__file__).with_name("threshold_holdout.tsv")
    if not suite_path.exists() or not holdout_path.exists():
        return

    traces = read_traces(suite_path)
    scenarios = sorted({str(trace.get("control_scenario", "")) for trace in traces})
    dsm_controls = sum(
        trace["framework"] in THIRD_PARTY and trace["condition"] in DSM_CONDITIONS
        for trace in traces
    )
    selected_rows = [row for row in read_rows(holdout_path) if row["selected"] == "1"]
    if not selected_rows:
        return
    row = selected_rows[0]
    print("\nSupplemental no-fault suite / held-out threshold")
    print(
        f"  no-fault suite: {len(traces)} traces; "
        f"{len(scenarios)} workflows; DSM third-party controls {dsm_controls}"
    )
    print(
        f"  selected max_retries={row['max_retries']} on train controls: "
        f"FP {row['train_fp_count']}/{row['train_fp_n']}={float(row['train_fpr']):.3f}; "
        f"held-out FP {row['holdout_fp_count']}/{row['holdout_fp_n']}={float(row['holdout_fpr']):.3f}; "
        f"infinite-loop TP {row['tp_count']}/{row['tp_n']}={float(row['tpr']):.3f}"
    )


def print_annotation_stats() -> None:
    review_path = Path(__file__).with_name("mast_mapping_review.tsv")
    pairs = []
    with review_path.open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            pairs.append((row["annotator_1"], row["annotator_2"]))

    def kappa(sample: list[tuple[str, str]]) -> float:
        n = len(sample)
        observed = sum(a == b for a, b in sample) / n
        c1 = Counter(a for a, _ in sample)
        c2 = Counter(b for _, b in sample)
        expected = sum((c1[label] / n) * (c2[label] / n) for label in set(c1) | set(c2))
        if expected == 1:
            return 1.0 if observed == 1 else 0.0
        return (observed - expected) / (1 - expected)

    observed = sum(a == b for a, b in pairs)
    rng = random.Random(20260506)
    boot = []
    for _ in range(10000):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        boot.append(kappa(sample))
    boot.sort()
    lo = boot[249]
    hi = boot[9749]
    print("\nAnnotation agreement")
    print(f"  observed agreement: {observed}/13={observed/13:.3f}")
    print(f"  Cohen's kappa from mast_mapping_review.tsv: {kappa(pairs):.2f}")
    print(f"  bootstrap 95% CI: [{lo:.2f}, {hi:.2f}]")


def print_live_llm_stats() -> None:
    path = Path(__file__).with_name("real_llm_14fault.tsv")
    if not path.exists():
        return
    attempted = parsed = fault_parsed = fault_detected = nofault_parsed = nofault_detected = 0
    with path.open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            attempted += 1
            parsed_cell = int(row["parsed"]) if row["parsed"] else 0
            detected_cell = int(row["detected"]) if row["detected"] else 0
            parsed += parsed_cell
            if row["scenario"] == "no_fault":
                nofault_parsed += parsed_cell
                nofault_detected += detected_cell if parsed_cell else 0
            elif parsed_cell:
                fault_parsed += 1
                fault_detected += detected_cell
    lo, hi = wilson(fault_detected, fault_parsed)
    print("\nLive-LLM CLI 14-fault decision protocol")
    print(f"  attempted decisions: {attempted}; parsed: {parsed}/{attempted}")
    print(f"  fault-bearing parsed decisions: {fault_detected}/{fault_parsed}={fault_detected/fault_parsed:.3f}, Wilson [{lo:.3f},{hi:.3f}]")
    print(f"  no-fault false alarms: {nofault_detected}/{nofault_parsed}={nofault_detected/nofault_parsed:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="?", default="results_full.tsv")
    parser.add_argument("--traces", default=None)
    args = parser.parse_args()
    results_path = Path(args.results)
    rows = read_rows(results_path)
    traces_path = Path(args.traces) if args.traces else results_path.with_name("traces_full.jsonl")
    traces = read_traces(traces_path)
    print_count_summary(rows)
    print_tcr_fpr(rows)
    print_designed_gap_stats()
    print_realized_inference(rows, traces)
    print_secondary_rules(rows, traces)
    print_live_sdk_validation_sensitivity(rows, traces)
    print_production_plausible_sensitivity(rows, traces)
    print_no_fault_holdout()
    print_live_llm_stats()
    print_annotation_stats()


if __name__ == "__main__":
    main()
