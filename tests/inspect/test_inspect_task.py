"""Tests for the Inspect eval port (agenttelemetry_inspect).

Includes the oracle closure test: the paper's rule-based detectors, run over
the frozen dataset at generation time, must reproduce the published
aggregates (README benchmark table / AIware 2026 Table 2). This is the
mechanical guarantee that the Inspect port preserves the benchmark's scoring
semantics.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from agenttelemetry_inspect.agenttelemetry_inspect import (
    CONDITIONS,
    FAULT_TYPES,
    NO_FAULT,
    _extract_verdict,
    _normalize_fault_type,
    agent_telemetry,
    fault_detection_scorer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = REPO_ROOT / "src" / "agenttelemetry_inspect" / "data" / "traces_v1.jsonl"
RESULTS_TSV = REPO_ROOT / "benchmarks" / "results_full.tsv"


@pytest.fixture(scope="module")
def rows():
    with open(DATA_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]


# -- Dataset integrity ---------------------------------------------------------


class TestDatasetIntegrity:
    def test_sample_counts(self, rows):
        assert len(rows) == 170
        by_condition = {}
        for r in rows:
            by_condition.setdefault(r["metadata"]["condition"], []).append(r)
        assert len(by_condition["agenttelemetry"]) == 119  # 7x14 faults + 7x3 controls
        for baseline in ("vanilla_otel", "otel_genai", "openinference"):
            assert len(by_condition[baseline]) == 17  # 14 faults + 3 controls

    def test_targets_valid(self, rows):
        for r in rows:
            assert r["target"] in FAULT_TYPES + (NO_FAULT,)
            assert r["metadata"]["is_control"] == (r["target"] == NO_FAULT)

    def test_no_label_string_leaks(self, rows):
        """The fault label never appears literally in the model input."""
        for r in rows:
            if not r["metadata"]["is_control"]:
                assert r["metadata"]["fault_type"] not in r["input"], r["id"]

    def test_controls_have_grounding_activity(self, rows):
        """Every control trace shows tool/retrieval/delegation activity, so
        the structural hallucination signal (no grounding at all) stays sound."""
        markers = (
            '"agent_span_kind": "TOOL_CALL"',
            '"agent_span_kind": "RETRIEVAL"',
            '"agent_span_kind": "DELEGATION"',
            "tool.name",
            "gen_ai.tool.name",
            '"openinference.span.kind": "TOOL"',
            '"openinference.span.kind": "RETRIEVER"',
            "tool-",
            "retriev",
            "delegate",
        )
        for r in rows:
            if r["metadata"]["is_control"]:
                assert any(m in r["input"] for m in markers), r["id"]

    def test_no_run_errors(self, rows):
        assert all(r["metadata"]["run_error"] is None for r in rows)


# -- Oracle closure: the port reproduces the published aggregates --------------


class TestOracleClosure:
    """metadata.oracle_detected is stamped at generation time by running the
    repo's own per-condition rule detectors (with ground-truth access, as in
    the paper) over each generated trace."""

    def test_dsm_aggregate_matches_readme(self, rows):
        fault = [
            r for r in rows
            if r["metadata"]["condition"] == "agenttelemetry"
            and not r["metadata"]["is_control"]
        ]
        detected = sum(r["metadata"]["oracle_detected"] for r in fault)
        assert (detected, len(fault)) == (60, 98)  # README: DSM (metadata) 0.612

    def test_reference_adapter_upper_bound(self, rows):
        """Paper Table 2: the conformance-complete custom adapter detects 14/14."""
        custom = [
            r for r in rows
            if r["metadata"]["condition"] == "agenttelemetry"
            and r["metadata"]["framework"] == "custom"
            and not r["metadata"]["is_control"]
        ]
        assert len(custom) == 14
        assert all(r["metadata"]["oracle_detected"] for r in custom)

    @pytest.mark.parametrize("baseline", ["vanilla_otel", "otel_genai", "openinference"])
    def test_baseline_aggregates(self, rows, baseline):
        fault = [
            r for r in rows
            if r["metadata"]["condition"] == baseline and not r["metadata"]["is_control"]
        ]
        detected = sum(r["metadata"]["oracle_detected"] for r in fault)
        assert (detected, len(fault)) == (6, 14)  # README: 0.429 per baseline

    def test_controls_clean_under_rules(self, rows):
        for r in rows:
            if r["metadata"]["is_control"]:
                assert r["metadata"]["oracle_false_fires"] == [], r["id"]

    def test_dsm_cells_match_committed_tsv(self, rows):
        """Per-cell agreement with benchmarks/results_full.tsv (the corpus the
        README table is computed from), metadata_only condition, same persona."""
        if not RESULTS_TSV.exists():
            pytest.skip("results_full.tsv not present")
        tsv = {}
        with open(RESULTS_TSV) as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row["model"] == "claude-sonnet-4" and row["condition"] == "metadata_only":
                    tsv[(row["framework"], row["fault_type"])] = int(row["faults_detected"]) > 0
        mismatches = []
        for r in rows:
            m = r["metadata"]
            if m["condition"] != "agenttelemetry" or m["is_control"]:
                continue
            framework = m["framework"]
            key = (framework, m["fault_type"])
            if key in tsv and tsv[key] != m["oracle_detected"]:
                mismatches.append((key, tsv[key], m["oracle_detected"]))
        assert not mismatches, mismatches


# -- Verdict parsing ------------------------------------------------------------


class TestVerdictParsing:
    def test_clean_json(self):
        v = _extract_verdict('{"fault_detected": true, "fault_type": "infinite_loop"}')
        assert v == {"fault_detected": True, "fault_type": "infinite_loop"}

    def test_json_after_prose(self):
        text = (
            "The trace shows the same tool called five times.\n\n"
            '{"fault_detected": true, "fault_type": "infinite_loop"}'
        )
        assert _extract_verdict(text)["fault_type"] == "infinite_loop"

    def test_fenced_json(self):
        text = '```json\n{"fault_detected": false, "fault_type": null}\n```'
        v = _extract_verdict(text)
        assert v == {"fault_detected": False, "fault_type": None}

    def test_last_verdict_wins(self):
        text = (
            '{"fault_detected": true, "fault_type": "timeout"}\n'
            'On reflection: {"fault_detected": false, "fault_type": null}'
        )
        assert _extract_verdict(text)["fault_detected"] is False

    def test_garbage_returns_none(self):
        assert _extract_verdict("no verdict here") is None
        assert _extract_verdict("") is None

    def test_normalize_fault_type(self):
        assert _normalize_fault_type("Infinite Loop") == "infinite_loop"
        assert _normalize_fault_type("stale-retrieval") == "stale_retrieval"
        assert _normalize_fault_type(None) is None
        assert _normalize_fault_type("none") is None
        assert _normalize_fault_type("no_fault") is None


# -- Scorer semantics (through the real Score path) ------------------------------


def _score_completion(rows, sample_id, completion):
    import asyncio

    from inspect_ai.model import ModelOutput
    from inspect_ai.scorer import Target
    from inspect_ai.solver import TaskState

    record = next(r for r in rows if r["id"] == sample_id)
    state = TaskState(
        model="mockllm/model",
        sample_id=sample_id,
        epoch=0,
        input=record["input"],
        messages=[],
        output=ModelOutput.from_content("mockllm/model", completion),
        metadata=dict(record["metadata"]),
    )
    scorer_fn = fault_detection_scorer()
    return asyncio.run(scorer_fn(state, Target(record["target"])))


class TestScorerSemantics:
    def test_correct_fault_answer(self, rows):
        score = _score_completion(
            rows,
            "agenttelemetry:custom:infinite_loop:t0",
            '{"fault_detected": true, "fault_type": "infinite_loop"}',
        )
        assert score.value == "C"
        assert score.metadata["detected"] is True
        assert score.metadata["class_correct"] is True

    def test_detected_wrong_class_counts_for_fdr_only(self, rows):
        score = _score_completion(
            rows,
            "agenttelemetry:custom:infinite_loop:t0",
            '{"fault_detected": true, "fault_type": "timeout"}',
        )
        assert score.value == "I"
        assert score.metadata["detected"] is True  # FDR credit
        assert score.metadata["class_correct"] is False

    def test_control_pass_and_fail(self, rows):
        ok = _score_completion(
            rows,
            "agenttelemetry:custom:no_fault:t0",
            '{"fault_detected": false, "fault_type": null}',
        )
        assert ok.value == "C" and ok.metadata["is_control"] is True
        bad = _score_completion(
            rows,
            "agenttelemetry:custom:no_fault:t0",
            '{"fault_detected": true, "fault_type": "cost_explosion"}',
        )
        assert bad.value == "I" and bad.metadata["detected"] is True

    def test_unparseable_never_passes(self, rows):
        for sample_id in (
            "agenttelemetry:custom:infinite_loop:t0",
            "agenttelemetry:custom:no_fault:t0",
        ):
            score = _score_completion(rows, sample_id, "I cannot analyze this trace.")
            assert score.value == "I"
            assert score.metadata["parse_error"] is True

    def test_oracle_answers_score_perfectly(self, rows):
        """A responder that reports the rule-detector outcome (detected cells
        get the true class, undetectable cells report no fault observable)
        achieves ceiling accuracy on detectable cells and on controls."""
        for r in rows:
            m = r["metadata"]
            if m["is_control"] or m["oracle_detected"]:
                if m["is_control"]:
                    completion = '{"fault_detected": false, "fault_type": null}'
                else:
                    completion = json.dumps(
                        {"fault_detected": True, "fault_type": m["fault_type"]}
                    )
                score = _score_completion(rows, r["id"], completion)
                assert score.value == "C", r["id"]


# -- Task construction -----------------------------------------------------------


class TestTaskConstruction:
    def test_default_task(self):
        t = agent_telemetry()
        assert len(t.dataset) == 119

    @pytest.mark.parametrize("condition,expected", [
        ("vanilla_otel", 17), ("otel_genai", 17), ("openinference", 17),
    ])
    def test_baseline_conditions(self, condition, expected):
        assert len(agent_telemetry(condition=condition).dataset) == expected

    def test_framework_filter(self):
        assert len(agent_telemetry(frameworks="custom").dataset) == 17

    def test_fault_filter_keeps_controls(self):
        t = agent_telemetry(faults="infinite_loop")
        assert len(t.dataset) == 28  # 7 fault samples + 21 controls

    def test_invalid_arguments_raise(self):
        with pytest.raises(ValueError):
            agent_telemetry(condition="not_a_condition")
        with pytest.raises(ValueError):
            agent_telemetry(faults="not_a_fault")

    def test_all_conditions_enumerated(self):
        assert set(CONDITIONS) == {
            "agenttelemetry", "vanilla_otel", "otel_genai", "openinference",
        }
