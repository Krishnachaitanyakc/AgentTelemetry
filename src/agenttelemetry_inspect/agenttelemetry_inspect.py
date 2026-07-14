"""AgentTelemetry fault-detection eval for the Inspect framework.

The model is shown one execution trace of an LLM agent run (spans exported
by the AgentTelemetry fault-injection harness, the same harness behind the
AIware 2026 paper) and must decide whether a fault is present and, if so,
classify it against the paper's 14-fault taxonomy. Scoring is deterministic
string matching against the injected-fault ground truth; there is no model
judge and no sandbox.

Run (from a repository checkout):

    uv sync
    uv run inspect eval src/agenttelemetry_inspect/agenttelemetry_inspect.py@agent_telemetry \
        --model anthropic/claude-haiku-4-5 --limit 10

Task parameters:

    condition   which telemetry vocabulary the traces were rendered under:
                "agenttelemetry" (default; 9 typed span kinds, 7 framework
                adapters), "vanilla_otel", "otel_genai", or "openinference"
    frameworks  optional framework filter for the agenttelemetry condition,
                e.g. ["custom"] for the reference adapter where the paper's
                rule-based ceiling is 14/14
    faults      optional fault-type filter (values from the 14-fault taxonomy)

Interpreting scores: per-condition model FDR is bounded above by what the
telemetry vocabulary can express. The paper's rule-based reference on this
exact dataset detects 60/98 fault samples for the agenttelemetry condition
(1.000 on the reference adapter subset; adapter conformance gaps account
for the rest) and 6/14 for each baseline vocabulary. The fdr_detectable
metric restricts FDR to samples where the rule-based reference fires, so
its ceiling is 1.0 under every condition.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, json_dataset
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    metric,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState, generate, system_message

DATA_FILE = Path(__file__).resolve().parent / "data" / "traces_v1.jsonl"

CONDITIONS = ("agenttelemetry", "vanilla_otel", "otel_genai", "openinference")

FAULT_TYPES = (
    "wrong_tool",
    "hallucination",
    "infinite_loop",
    "context_overflow",
    "cost_explosion",
    "circular_delegation",
    "tool_failure",
    "timeout",
    "stale_retrieval",
    "guardrail_bypass",
    "planning_failure",
    "reasoning_loop",
    "agent_misroute",
    "memory_corruption",
)

NO_FAULT = "no_fault"

# The taxonomy and thresholds below are the paper's Table 2 detection
# signals. The rule-based reference detectors know these thresholds, so a
# fair model evaluation discloses the same spec sheet.
SYSTEM_PROMPT = """\
You are a reliability engineer analyzing telemetry from LLM agent systems.
You will be shown the execution trace of a single agent run, exported as a
JSON list of spans (fields: id, parent, name, agent_span_kind where the
instrumentation provides it, start_ms, duration_ms, status, attributes,
events). At most one fault was injected into the run; many runs are
fault-free.

Decide whether the trace shows evidence of a fault, and if so classify it
as exactly one of these 14 fault types (detection signal in parentheses):

1. wrong_tool (a tool call or delegation inconsistent with the agent task)
2. hallucination (substantial LLM output with no retrieval or tool grounding
   anywhere in the run, on a task that requires external information)
3. infinite_loop (the same tool called 3 or more times)
4. context_overflow (LLM input tokens growing more than 1.3x across
   consecutive calls, sustained)
5. cost_explosion (total LLM cost above $0.10 for the run)
6. circular_delegation (delegation cycle, e.g. agent A delegates to B and B
   back to A)
7. tool_failure (a tool span with error status)
8. timeout (error status or exception mentioning a timeout)
9. stale_retrieval (retrieval staleness above 3600 seconds)
10. guardrail_bypass (a guardrail outcome of "bypass" or "fail")
11. planning_failure (a plan with more than 10 steps)
12. reasoning_loop (2 or more reasoning spans with an identical
    reasoning chain)
13. agent_misroute (an agent span flagged as misrouted, or handled by a
    different agent than expected)
14. memory_corruption (a memory read span flagged as corrupted)

Base your judgment only on what the spans show. If the trace does not
contain evidence of any of the 14 fault types, report that no fault was
detected. Do not guess a fault type without span-level evidence.

End your reply with a single line containing only a JSON object in exactly
this form (fault_type must be one of the 14 names above, or null when no
fault is detected):

{"fault_detected": true, "fault_type": "infinite_loop"}
"""


def _normalize_fault_type(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if text in ("", "none", "null", NO_FAULT, "no_fault_detected"):
        return None
    return text


def _extract_verdict(completion: str) -> Optional[Dict[str, Any]]:
    """Find the last JSON object in the completion that carries a verdict."""
    candidates = re.findall(r"\{[^{}]*\}", completion or "")
    for text in reversed(candidates):
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict) and "fault_detected" in obj:
            return obj
    return None


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes"):
            return True
        if lowered in ("false", "no"):
            return False
    return None


def _fault_scores(scores: list) -> list:
    return [s for s in scores if not s.score.metadata.get("is_control")]


@metric
def fdr():
    """Fault Detection Rate: fraction of fault samples the model flagged."""

    def compute(scores: list) -> float:
        fault = _fault_scores(scores)
        if not fault:
            return 0.0
        return sum(1 for s in fault if s.score.metadata.get("detected")) / len(fault)

    return compute


@metric
def fdr_detectable():
    """FDR over fault samples the rule-based reference detects (ceiling 1.0)."""

    def compute(scores: list) -> float:
        fault = [
            s for s in _fault_scores(scores) if s.score.metadata.get("oracle_detected")
        ]
        if not fault:
            return 0.0
        return sum(1 for s in fault if s.score.metadata.get("detected")) / len(fault)

    return compute


@metric
def fpr():
    """False-positive rate: fraction of fault-free runs flagged as faulty."""

    def compute(scores: list) -> float:
        controls = [s for s in scores if s.score.metadata.get("is_control")]
        if not controls:
            return 0.0
        return sum(1 for s in controls if s.score.metadata.get("detected")) / len(
            controls
        )

    return compute


@metric
def classification_accuracy():
    """Correct fault class given a fault sample (detection and class both right)."""

    def compute(scores: list) -> float:
        fault = _fault_scores(scores)
        if not fault:
            return 0.0
        return sum(1 for s in fault if s.score.metadata.get("class_correct")) / len(
            fault
        )

    return compute


@scorer(
    metrics=[
        accuracy(),
        stderr(),
        fdr(),
        fdr_detectable(),
        fpr(),
        classification_accuracy(),
    ]
)
def fault_detection_scorer():
    """Deterministic scorer against the injected-fault ground truth."""

    async def score(state: TaskState, target: Target) -> Score:
        true_type = target.text
        is_control = true_type == NO_FAULT
        sample_meta = state.metadata or {}

        verdict = _extract_verdict(state.output.completion)
        parse_error = verdict is None
        detected = _coerce_bool(verdict.get("fault_detected")) if verdict else None
        predicted = _normalize_fault_type(verdict.get("fault_type")) if verdict else None
        if detected is None:
            # No parseable verdict: treat as a (wrong) non-answer, never a pass.
            detected = predicted is not None

        class_correct = (not is_control) and detected and predicted == true_type
        if is_control:
            correct = not detected and not parse_error
        else:
            correct = class_correct

        return Score(
            value=CORRECT if correct else INCORRECT,
            answer=json.dumps(
                {"fault_detected": detected, "fault_type": predicted}
            ),
            explanation=(
                f"target={true_type} predicted="
                f"{predicted if detected else NO_FAULT}"
                + (" (unparseable output)" if parse_error else "")
            ),
            metadata={
                "detected": bool(detected),
                "predicted_type": predicted,
                "true_type": true_type,
                "is_control": is_control,
                "class_correct": bool(class_correct),
                "parse_error": parse_error,
                "oracle_detected": bool(sample_meta.get("oracle_detected")),
                "condition": sample_meta.get("condition"),
                "framework": sample_meta.get("framework"),
            },
        )

    return score


def _as_list(value: Union[str, List[str], None]) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    return list(value)


@task
def agent_telemetry(
    condition: str = "agenttelemetry",
    frameworks: Union[str, List[str], None] = None,
    faults: Union[str, List[str], None] = None,
) -> Task:
    """Detect and classify injected faults in LLM agent telemetry traces.

    Args:
        condition: Telemetry vocabulary the traces were rendered under. One
            of "agenttelemetry", "vanilla_otel", "otel_genai",
            "openinference".
        frameworks: Optional framework-adapter filter (agenttelemetry
            condition only), e.g. "custom" for the reference adapter.
        faults: Optional filter of fault types to include (fault-free
            control samples are always kept).
    """
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}, got {condition!r}")
    framework_list = _as_list(frameworks)
    fault_list = _as_list(faults)
    if fault_list:
        unknown = set(fault_list) - set(FAULT_TYPES)
        if unknown:
            raise ValueError(f"unknown fault types: {sorted(unknown)}")

    def record_to_sample(record: Dict[str, Any]) -> Sample:
        return Sample(
            input=record["input"],
            target=record["target"],
            id=record["id"],
            metadata=dict(record.get("metadata") or {}),
        )

    dataset = json_dataset(str(DATA_FILE), sample_fields=record_to_sample)

    def keep(sample) -> bool:
        meta = sample.metadata or {}
        if meta.get("condition") != condition:
            return False
        if framework_list and meta.get("framework") not in framework_list:
            return False
        if fault_list and not meta.get("is_control") and meta.get("fault_type") not in fault_list:
            return False
        return True

    dataset = dataset.filter(keep)

    return Task(
        dataset=dataset,
        solver=[system_message(SYSTEM_PROMPT), generate()],
        scorer=fault_detection_scorer(),
        version=1,
        metadata={
            "paper_doi": "10.1145/3805760.3814931",
            "dataset_version": "v1",
        },
    )
