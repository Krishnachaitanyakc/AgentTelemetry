"""Main experiment runner for real LLM validation.

Phase 1: Clean traces      — 20Q x 13 models             = 260 runs
Phase 2: FULL privacy       — 5Q x 13 models              = 65 runs
Phase 3: Fault injection    — 5 faults x 2Q x 13 models   = 130 runs
Phase 4: Overhead baseline  — 5Q x 3 models uninstrumented = 15 runs
TOTAL                                                      = 470 runs
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure src is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from agenttelemetry.core.tracer import AgentTelemetryProvider
from agenttelemetry.core.privacy import PrivacyLevel

from experiments.real_llm.config import (
    MODELS,
    BudgetTracker,
    ModelConfig,
    create_client,
)
from experiments.real_llm.questions import QUESTIONS, Question
from experiments.real_llm.agent import run_agent
from experiments.real_llm.fault_conditions import FAULT_CONDITIONS


RESULTS_DIR = PROJECT_ROOT / "results" / "real_llm"
TRACES_DIR = RESULTS_DIR / "traces"
CHECKPOINT_FILE = RESULTS_DIR / "checkpoint.json"
CALL_SPACING_S = 0.2  # 200ms between API calls


def setup_dirs():
    """Create output directories."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)


def load_checkpoint() -> Dict[str, Any]:
    """Load checkpoint for resume capability."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"completed_phases": [], "completed_runs": []}


def save_checkpoint(checkpoint: Dict[str, Any]):
    """Save checkpoint."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)


def run_key(phase: str, model: str, question_id: int, fault: str = "") -> str:
    """Generate a unique key for a run."""
    return f"{phase}:{model}:Q{question_id}" + (f":{fault}" if fault else "")


def preflight_test(budget: BudgetTracker) -> bool:
    """Test connectivity with gpt-4o-mini on Q1."""
    print("\n=== PRE-FLIGHT CHECK ===")
    q = QUESTIONS[0]

    for model_key in ["gpt-4o-mini"]:
        config = MODELS[model_key]
        print(f"  Testing {config.display_name}...", end=" ", flush=True)
        try:
            client = create_client(config)
            provider = AgentTelemetryProvider(
                service_name="preflight",
                privacy_level=PrivacyLevel.FULL,
            )
            json_exporter = provider.add_json_exporter(
                str(TRACES_DIR / "preflight.jsonl")
            )
            provider.setup()
            tracer = provider.get_tracer("preflight")

            result = run_agent(
                client, config, q.text,
                tracer=tracer, budget=budget,
            )
            provider.shutdown()

            if result["error"]:
                print(f"ERROR: {result['error']}")
                return False

            print(f"OK (tools: {result['tool_calls_made']}, tokens: {result['total_input_tokens']+result['total_output_tokens']})")

        except Exception as e:
            print(f"FAILED: {e}")
            return False

    # Test Anthropic if key available
    if os.environ.get("ANTHROPIC_API_KEY"):
        for model_key in ["claude-haiku-4-5"]:
            if model_key not in MODELS:
                continue
            config = MODELS[model_key]
            print(f"  Testing {config.display_name}...", end=" ", flush=True)
            try:
                client = create_client(config)
                provider = AgentTelemetryProvider(
                    service_name="preflight",
                    privacy_level=PrivacyLevel.FULL,
                )
                json_exporter = provider.add_json_exporter(
                    str(TRACES_DIR / "preflight_anthropic.jsonl")
                )
                provider.setup()
                tracer = provider.get_tracer("preflight")

                result = run_agent(
                    client, config, q.text,
                    tracer=tracer, budget=budget,
                )
                provider.shutdown()

                if result["error"]:
                    print(f"ERROR: {result['error']}")
                    # Don't fail — Anthropic is optional
                else:
                    print(f"OK (tools: {result['tool_calls_made']})")
            except Exception as e:
                print(f"SKIPPING (Anthropic not available): {e}")
    else:
        print("  Anthropic: SKIPPED (no API key)")

    return True


def get_available_models() -> List[str]:
    """Return model keys that have valid API credentials."""
    available = []
    for key, config in MODELS.items():
        if config.provider == "openai" and os.environ.get("OPENAI_API_KEY"):
            available.append(key)
        elif config.provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            available.append(key)
    return available


def run_phase1(budget: BudgetTracker, checkpoint: Dict[str, Any]):
    """Phase 1: Clean traces — 20 questions x all available models."""
    print("\n=== PHASE 1: Clean Traces ===")
    models = get_available_models()
    questions = QUESTIONS

    results = []
    for model_key in models:
        config = MODELS[model_key]

        # Setup tracing for this model
        provider = AgentTelemetryProvider(
            service_name="real_llm_experiment",
            privacy_level=PrivacyLevel.FULL,
        )
        trace_file = str(TRACES_DIR / f"phase1_{model_key}.jsonl")
        json_exporter = provider.add_json_exporter(trace_file)
        provider.setup()
        tracer = provider.get_tracer("experiment")

        client = create_client(config)

        for q in questions:
            key = run_key("phase1", model_key, q.id)
            if key in checkpoint.get("completed_runs", []):
                print(f"  SKIP {config.display_name} Q{q.id} (already done)")
                continue

            if not budget.can_afford(config.model_id):
                print(f"  SKIP {config.display_name} Q{q.id} (budget)")
                continue

            print(f"  {config.display_name} Q{q.id} ({q.category})...", end=" ", flush=True)

            try:
                result = run_agent(
                    client, config, q.text,
                    tracer=tracer, budget=budget,
                )
                result["model"] = model_key
                result["question_id"] = q.id
                result["phase"] = "phase1"
                results.append(result)

                tools_str = ",".join(result["tool_calls_made"][:4])
                print(f"OK ({result['iterations']}it, {tools_str})")

                checkpoint.setdefault("completed_runs", []).append(key)
                save_checkpoint(checkpoint)

            except Exception as e:
                print(f"ERROR: {e}")
                result = {
                    "model": model_key,
                    "question_id": q.id,
                    "phase": "phase1",
                    "error": str(e),
                }
                results.append(result)

            time.sleep(CALL_SPACING_S)

        provider.shutdown()

    # Save phase results
    with open(RESULTS_DIR / "phase1_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    checkpoint.setdefault("completed_phases", []).append("phase1")
    save_checkpoint(checkpoint)
    print(f"\nPhase 1 complete. Budget: {budget.summary()}")


def run_phase2(budget: BudgetTracker, checkpoint: Dict[str, Any]):
    """Phase 2: FULL privacy — 5 questions x all models with full content capture."""
    print("\n=== PHASE 2: Privacy Level Comparison ===")
    models = get_available_models()
    # Use Q1-Q5 for privacy comparison
    questions = [q for q in QUESTIONS if q.id <= 5]

    results = []
    for privacy_level in [PrivacyLevel.NONE, PrivacyLevel.METADATA_ONLY, PrivacyLevel.FULL]:
        for model_key in models:
            config = MODELS[model_key]

            provider = AgentTelemetryProvider(
                service_name="real_llm_experiment",
                privacy_level=privacy_level,
            )
            trace_file = str(TRACES_DIR / f"phase2_{model_key}_{privacy_level.value}.jsonl")
            json_exporter = provider.add_json_exporter(trace_file)
            provider.setup()
            tracer = provider.get_tracer("experiment")

            client = create_client(config)

            for q in questions:
                key = run_key("phase2", model_key, q.id, privacy_level.value)
                if key in checkpoint.get("completed_runs", []):
                    print(f"  SKIP {config.display_name} Q{q.id} {privacy_level.value} (done)")
                    continue

                if not budget.can_afford(config.model_id):
                    print(f"  SKIP {config.display_name} Q{q.id} (budget)")
                    continue

                print(f"  {config.display_name} Q{q.id} [{privacy_level.value}]...", end=" ", flush=True)

                try:
                    result = run_agent(
                        client, config, q.text,
                        tracer=tracer, budget=budget,
                    )
                    result["model"] = model_key
                    result["question_id"] = q.id
                    result["phase"] = "phase2"
                    result["privacy_level"] = privacy_level.value
                    results.append(result)
                    print("OK")

                    checkpoint.setdefault("completed_runs", []).append(key)
                    save_checkpoint(checkpoint)

                except Exception as e:
                    print(f"ERROR: {e}")

                time.sleep(CALL_SPACING_S)

            provider.shutdown()

    with open(RESULTS_DIR / "phase2_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    checkpoint.setdefault("completed_phases", []).append("phase2")
    save_checkpoint(checkpoint)
    print(f"\nPhase 2 complete. Budget: {budget.summary()}")


def run_phase3(budget: BudgetTracker, checkpoint: Dict[str, Any]):
    """Phase 3: Fault injection — 5 faults x 2 questions x all models."""
    print("\n=== PHASE 3: Fault Injection ===")
    models = get_available_models()

    results = []
    for fault in FAULT_CONDITIONS:
        for model_key in models:
            config = MODELS[model_key]

            provider = AgentTelemetryProvider(
                service_name="real_llm_experiment",
                privacy_level=PrivacyLevel.FULL,
            )
            trace_file = str(TRACES_DIR / f"phase3_{model_key}_{fault.name}.jsonl")
            json_exporter = provider.add_json_exporter(trace_file)
            provider.setup()
            tracer = provider.get_tracer("experiment")

            client = create_client(config)

            for qid in fault.question_ids:
                q = next(qq for qq in QUESTIONS if qq.id == qid)
                key = run_key("phase3", model_key, q.id, fault.name)
                if key in checkpoint.get("completed_runs", []):
                    print(f"  SKIP {config.display_name} Q{q.id} [{fault.name}] (done)")
                    continue

                if not budget.can_afford(config.model_id):
                    print(f"  SKIP {config.display_name} Q{q.id} (budget)")
                    continue

                print(f"  {config.display_name} Q{q.id} [{fault.name}]...", end=" ", flush=True)

                try:
                    # Build kwargs and apply fault
                    kwargs = {
                        "client": client,
                        "config": config,
                        "question": q.text,
                        "tracer": tracer,
                        "budget": budget,
                    }
                    kwargs = fault.apply(kwargs)

                    result = run_agent(**kwargs)
                    result["model"] = model_key
                    result["question_id"] = q.id
                    result["phase"] = "phase3"
                    result["fault"] = fault.name
                    results.append(result)

                    tools_str = ",".join(result["tool_calls_made"][:4])
                    print(f"OK ({result['iterations']}it, {tools_str})")

                    checkpoint.setdefault("completed_runs", []).append(key)
                    save_checkpoint(checkpoint)

                except Exception as e:
                    print(f"ERROR: {e}")
                    results.append({
                        "model": model_key,
                        "question_id": q.id,
                        "phase": "phase3",
                        "fault": fault.name,
                        "error": str(e),
                    })

                time.sleep(CALL_SPACING_S)

            provider.shutdown()

    with open(RESULTS_DIR / "phase3_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    checkpoint.setdefault("completed_phases", []).append("phase3")
    save_checkpoint(checkpoint)
    print(f"\nPhase 3 complete. Budget: {budget.summary()}")


def run_phase4(budget: BudgetTracker, checkpoint: Dict[str, Any]):
    """Phase 4: Overhead baseline — 5Q x 3 models, uninstrumented."""
    print("\n=== PHASE 4: Overhead Baseline ===")
    # Use cheap models for overhead measurement
    overhead_models = ["gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini"]
    overhead_models = [m for m in overhead_models if m in get_available_models()]
    questions = [q for q in QUESTIONS if q.id <= 5]

    results = []
    for model_key in overhead_models:
        config = MODELS[model_key]
        client = create_client(config)

        for q in questions:
            key = run_key("phase4", model_key, q.id)
            if key in checkpoint.get("completed_runs", []):
                print(f"  SKIP {config.display_name} Q{q.id} (done)")
                continue

            if not budget.can_afford(config.model_id):
                print(f"  SKIP {config.display_name} Q{q.id} (budget)")
                continue

            # Run WITH instrumentation
            print(f"  {config.display_name} Q{q.id} [instrumented]...", end=" ", flush=True)
            provider = AgentTelemetryProvider(
                service_name="overhead_test",
                privacy_level=PrivacyLevel.FULL,
            )
            trace_file = str(TRACES_DIR / f"phase4_{model_key}_instrumented.jsonl")
            json_exporter = provider.add_json_exporter(trace_file)
            provider.setup()
            tracer = provider.get_tracer("overhead")

            start_instrumented = time.time()
            result_instr = run_agent(
                client, config, q.text,
                tracer=tracer, budget=budget,
            )
            time_instrumented = time.time() - start_instrumented
            provider.shutdown()
            print(f"OK ({time_instrumented:.2f}s)")

            time.sleep(CALL_SPACING_S)

            # Run WITHOUT instrumentation (no tracer)
            print(f"  {config.display_name} Q{q.id} [uninstrumented]...", end=" ", flush=True)
            start_raw = time.time()
            result_raw = run_agent(
                client, config, q.text,
                tracer=None, budget=budget,
            )
            time_raw = time.time() - start_raw
            print(f"OK ({time_raw:.2f}s)")

            overhead_pct = ((time_instrumented - time_raw) / time_raw * 100) if time_raw > 0 else 0

            results.append({
                "model": model_key,
                "question_id": q.id,
                "phase": "phase4",
                "time_instrumented_s": time_instrumented,
                "time_uninstrumented_s": time_raw,
                "overhead_pct": overhead_pct,
            })

            checkpoint.setdefault("completed_runs", []).append(key)
            save_checkpoint(checkpoint)
            time.sleep(CALL_SPACING_S)

    with open(RESULTS_DIR / "phase4_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    checkpoint.setdefault("completed_phases", []).append("phase4")
    save_checkpoint(checkpoint)
    print(f"\nPhase 4 complete. Budget: {budget.summary()}")


def main():
    """Run all experiment phases."""
    # Load env
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. Set in .env or environment.")
        sys.exit(1)

    setup_dirs()
    checkpoint = load_checkpoint()
    budget = BudgetTracker(total_budget=14.0, per_model_cap=3.0)

    print("=" * 60)
    print("AgentTelemetry Real LLM Experiment")
    print("=" * 60)
    print(f"Available models: {', '.join(get_available_models())}")
    print(f"Questions: {len(QUESTIONS)}")
    print(f"Budget: ${budget.total_budget:.2f}")

    # Pre-flight
    if not preflight_test(budget):
        print("\nPre-flight check failed. Aborting.")
        sys.exit(1)

    # Run phases
    if "phase1" not in checkpoint.get("completed_phases", []):
        run_phase1(budget, checkpoint)

    if "phase2" not in checkpoint.get("completed_phases", []):
        run_phase2(budget, checkpoint)

    if "phase3" not in checkpoint.get("completed_phases", []):
        run_phase3(budget, checkpoint)

    if "phase4" not in checkpoint.get("completed_phases", []):
        run_phase4(budget, checkpoint)

    print("\n" + "=" * 60)
    print("EXPERIMENT COMPLETE")
    print("=" * 60)
    print(budget.summary())
    print(f"\nResults in: {RESULTS_DIR}")
    print(f"Traces in:  {TRACES_DIR}")
    print("\nRun analysis: python experiments/real_llm/analyze.py")


if __name__ == "__main__":
    main()
