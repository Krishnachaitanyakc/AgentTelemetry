"""Deterministic dataset generator for the AgentTelemetry Inspect eval.

Re-runs the fault-injection harness from ``benchmarks/`` (the same apps,
mocks, and injector the AIware 2026 paper used), normalizes the exported
spans, and writes the frozen sample file that ships with the package at
``src/agenttelemetry_inspect/data/traces_v1.jsonl``.

Regeneration requires a repository checkout (the ``benchmarks`` package is
not part of the wheel):

    PYTHONPATH=src:. python -m agenttelemetry_inspect.generate_dataset

The eval task itself (``agenttelemetry_inspect.py``) only reads the frozen
JSONL and does not import this module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parents[1]

# The harness lives at the repo root, outside the installable package.
if not (_REPO_ROOT / "benchmarks").is_dir():
    raise ImportError(
        "Dataset regeneration requires an AgentTelemetry repository checkout "
        "(the benchmarks/ package is not shipped in the wheel)."
    )
for p in (str(_REPO_ROOT / "src"), str(_REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import os

from agenttelemetry import AgentTelemetryProvider
from agenttelemetry.core.privacy import PrivacyLevel

from benchmarks.faults import FaultInjector, FaultType
from benchmarks.mocks import MockAnthropicClient
from benchmarks.run_benchmarks import (
    _analyze_traces,
    _analyze_traces_genai,
    _analyze_traces_openinference,
    _analyze_traces_vanilla,
    _get_app_runner,
)
from benchmarks.apps.otel_genai.app import run_otel_genai_agent
from benchmarks.apps.openinference.app import run_openinference_agent
from benchmarks.apps.vanilla_otel.app import run_vanilla_agent


SEED = 42
RATE = 1.0
MAX_ITERATIONS = 5
PERSONA = "claude-sonnet-4"  # mock behavior is message-hash driven; persona only names the model
DATASET_VERSION = "v1"

DSM_FRAMEWORKS = [
    "custom", "langchain", "crewai", "autogen",
    "anthropic_sdk", "openai_sdk", "llamaindex",
]

BASELINE_RUNNERS = {
    "vanilla_otel": run_vanilla_agent,
    "otel_genai": run_otel_genai_agent,
    "openinference": run_openinference_agent,
}

CONDITION_ANALYZERS = {
    "agenttelemetry": _analyze_traces,
    "vanilla_otel": _analyze_traces_vanilla,
    "otel_genai": _analyze_traces_genai,
    "openinference": _analyze_traces_openinference,
}

CONDITION_LABELS = {
    "agenttelemetry": "AgentTelemetry DSM span taxonomy (9 typed span kinds, metadata capture)",
    "vanilla_otel": "vanilla OpenTelemetry spans (no agent-specific span kinds)",
    "otel_genai": "OpenTelemetry GenAI semantic conventions (gen_ai.* attributes)",
    "openinference": "OpenInference semantic conventions (openinference.span.kind)",
}

FAULTS = [ft for ft in FaultType if ft is not FaultType.NONE]

# Control-task candidates. The default app task comes first so that controls
# are not separable from fault samples by task string alone; the generator
# keeps the first CONTROLS_PER_APP candidates whose benign trace shows
# grounding activity (tool, retrieval, or delegation spans), which keeps the
# structural hallucination signal (long output with no grounding) sound.
CONTROL_TASK_POOL = [
    "Find the population of the ten largest European cities",
    "Compile a comparison of open-source vector databases",
    "What are the current best practices for securing Kubernetes clusters?",
    "Collect statistics on renewable energy adoption in 2025",
    "Investigate recent advances in battery chemistry",
    "Identify the most active contributors to the LLVM project this year",
    "Research how major airlines handle overbooking compensation",
    "Summarize the state of WebAssembly support across browsers",
]
CONTROLS_PER_APP = 3

_VOLATILE_MS_ATTRS = ("tool.latency_ms",)


def _run_cell(
    condition: str,
    framework: str,
    fault: FaultType,
    task: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Run one harness cell; returns (raw_spans, ground_truth, run_result)."""
    injector = FaultInjector(fault, rate=RATE, seed=SEED)
    client = MockAnthropicClient(default_model=PERSONA, fault_injector=injector)

    provider = AgentTelemetryProvider(
        service_name=f"bench-{framework}",
        privacy_level=PrivacyLevel.METADATA_ONLY,
    )
    exporter = provider.add_json_exporter(os.devnull)
    provider.setup(set_global=False)

    if condition == "agenttelemetry":
        runner = _get_app_runner(framework)
    else:
        runner = BASELINE_RUNNERS[condition]
    if runner is None:
        raise RuntimeError(f"No runner for framework {framework!r}")

    kwargs: Dict[str, Any] = dict(
        mock_client=client,
        provider=provider,
        model=PERSONA,
        max_iterations=MAX_ITERATIONS,
        fault_injector=injector,
    )
    if task is not None:
        kwargs["task"] = task

    try:
        result = runner(**kwargs)
    except Exception as e:  # mirror run_benchmarks: keep whatever spans exported
        result = {"iterations": 0, "steps": [], "error": str(e)}

    spans = exporter.get_exported_spans()
    provider.shutdown()
    return spans, injector.get_ground_truth(), result


def _normalize_spans(raw_spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stable, readable rendering of exported spans.

    Volatile fields (hex ids, wall-clock timestamps, sub-ms latencies) are
    remapped or rounded so that regeneration is structurally reproducible.
    """
    ordered = sorted(raw_spans, key=lambda s: (s.get("start_time_ns") or 0))
    if not ordered:
        return []
    t0 = ordered[0].get("start_time_ns") or 0
    id_map = {s["span_id"]: f"s{i + 1:02d}" for i, s in enumerate(ordered)}

    out: List[Dict[str, Any]] = []
    for s in ordered:
        attrs = dict(s.get("attributes") or {})
        attrs.pop("agenttelemetry.span.kind", None)
        for key in _VOLATILE_MS_ATTRS:
            if key in attrs and isinstance(attrs[key], (int, float)):
                attrs[key] = round(attrs[key])
        if isinstance(attrs.get("llm.cost"), float):
            attrs["llm.cost"] = round(attrs["llm.cost"], 6)

        norm: Dict[str, Any] = {
            "id": id_map[s["span_id"]],
            "parent": id_map.get(s.get("parent_span_id")),
            "name": s.get("name", ""),
        }
        if s.get("agent_span_kind"):
            norm["agent_span_kind"] = s["agent_span_kind"]
        start_ns = s.get("start_time_ns") or t0
        norm["start_ms"] = round((start_ns - t0) / 1e6)
        norm["duration_ms"] = round(s.get("duration_ms") or 0)
        status = s.get("status") or {}
        if status.get("code") and status["code"] != "UNSET":
            norm["status"] = {"code": status["code"]}
            if status.get("description"):
                norm["status"]["description"] = str(status["description"])[:300]
        if attrs:
            norm["attributes"] = attrs
        events = []
        for e in s.get("events") or []:
            ev: Dict[str, Any] = {"name": e.get("name", "")}
            ea = e.get("attributes") or {}
            for k in ("exception.type", "exception.message"):
                if ea.get(k):
                    ev[k] = str(ea[k])[:300]
            events.append(ev)
        if events:
            norm["events"] = events
        out.append(norm)
    return out


def _render_input(condition: str, task: str, spans: List[Dict[str, Any]]) -> str:
    span_lines = ",\n".join("  " + json.dumps(s, sort_keys=True) for s in spans)
    return (
        "Below is the execution trace of one LLM agent run, exported as spans.\n"
        f"Agent task: {task}\n"
        f"Instrumentation: {CONDITION_LABELS[condition]}\n"
        f"Spans ({len(spans)}):\n"
        "[\n" + span_lines + "\n]"
    )


def _has_grounding_activity(raw_spans: List[Dict[str, Any]]) -> bool:
    for s in raw_spans:
        kind = s.get("agent_span_kind") or ""
        name = (s.get("name") or "").lower()
        attrs = s.get("attributes") or {}
        if kind in ("TOOL_CALL", "RETRIEVAL", "DELEGATION"):
            return True
        if attrs.get("tool.name") or attrs.get("gen_ai.tool.name"):
            return True
        if attrs.get("openinference.span.kind") in ("TOOL", "RETRIEVER"):
            return True
        if name.startswith("tool-") or "retriev" in name or "delegate" in name:
            return True
    return False


def _oracle_all_detectors(
    condition: str, raw_spans: List[Dict[str, Any]]
) -> List[str]:
    """Which rule detectors fire with NO ground truth (false-positive sweep)."""
    analyzer = CONDITION_ANALYZERS[condition]
    fired = []
    for ft in FAULTS:
        detected, _, _, _ = analyzer(raw_spans, ft, [])
        if detected:
            fired.append(ft.value)
    return fired


def _default_task(condition: str, framework: str) -> str:
    if condition == "agenttelemetry":
        runner = _get_app_runner(framework)
    else:
        runner = BASELINE_RUNNERS[condition]
    import inspect as _inspect

    sig = _inspect.signature(runner)
    return sig.parameters["task"].default


def _make_sample(
    condition: str,
    framework: str,
    fault: FaultType,
    task: str,
    variant: str,
) -> Dict[str, Any]:
    raw_spans, ground_truth, result = _run_cell(condition, framework, fault, task=task)
    analyzer = CONDITION_ANALYZERS[condition]
    if fault is FaultType.NONE:
        oracle_detected = False
        oracle_false_fires = _oracle_all_detectors(condition, raw_spans)
    else:
        oracle_detected, _, _, _ = analyzer(raw_spans, fault, ground_truth)
        oracle_false_fires = []

    spans = _normalize_spans(raw_spans)
    sample_id = f"{condition}:{framework}:{fault.value}:{variant}"
    return {
        "id": sample_id,
        "input": _render_input(condition, task, spans),
        "target": fault.value,
        "metadata": {
            "condition": condition,
            "framework": framework,
            "fault_type": fault.value,
            "is_control": fault is FaultType.NONE,
            "task": task,
            "n_spans": len(spans),
            "oracle_detected": oracle_detected,
            "oracle_false_fires": oracle_false_fires,
            "ground_truth_events": len(ground_truth),
            "run_error": result.get("error"),
            "harness": {
                "seed": SEED,
                "rate": RATE,
                "max_iterations": MAX_ITERATIONS,
                "persona": PERSONA,
                "dataset_version": DATASET_VERSION,
            },
        },
    }


def generate(output: Path, verbose: bool = True) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []

    cells: List[Tuple[str, str]] = [("agenttelemetry", fw) for fw in DSM_FRAMEWORKS]
    cells += [(cond, "reference") for cond in BASELINE_RUNNERS]

    for condition, framework in cells:
        default_task = _default_task(condition, framework)

        for fault in FAULTS:
            sample = _make_sample(condition, framework, fault, default_task, "t0")
            samples.append(sample)
            if verbose:
                mark = "+" if sample["metadata"]["oracle_detected"] else "-"
                print(f"  [{mark}] {sample['id']}  spans={sample['metadata']['n_spans']}")

        # Controls: default task first, then screened variants.
        n_controls = 0
        for ti, task in enumerate([default_task] + CONTROL_TASK_POOL):
            if n_controls >= CONTROLS_PER_APP:
                break
            raw_spans, _, result = _run_cell(condition, framework, FaultType.NONE, task=task)
            if result.get("error") or not _has_grounding_activity(raw_spans):
                if verbose:
                    print(f"  [skip control] {condition}:{framework} task#{ti} (no grounding activity)")
                continue
            sample = _make_sample(condition, framework, FaultType.NONE, task, f"t{ti}")
            samples.append(sample)
            n_controls += 1
        if n_controls < CONTROLS_PER_APP:
            raise RuntimeError(
                f"Only {n_controls} grounded control tasks found for "
                f"{condition}:{framework}; extend CONTROL_TASK_POOL."
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        for s in samples:
            f.write(json.dumps(s, sort_keys=True) + "\n")

    if verbose:
        n_faults = sum(1 for s in samples if not s["metadata"]["is_control"])
        n_controls = len(samples) - n_faults
        print(f"\nWrote {len(samples)} samples ({n_faults} fault, {n_controls} control) to {output}")
        for cond in CONDITION_ANALYZERS:
            fault_s = [s for s in samples if s["metadata"]["condition"] == cond and not s["metadata"]["is_control"]]
            if fault_s:
                agg = sum(s["metadata"]["oracle_detected"] for s in fault_s) / len(fault_s)
                print(f"  rule-detector ceiling [{cond}]: {agg:.3f} ({sum(s['metadata']['oracle_detected'] for s in fault_s)}/{len(fault_s)})")
    return samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(_PACKAGE_DIR / "data" / f"traces_{DATASET_VERSION}.jsonl"),
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    generate(Path(args.output), verbose=not args.quiet)
