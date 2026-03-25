"""Matched-iteration control experiment for SWE-bench.

Addresses the iteration confound identified by reviewers:
- Baseline uses 8 iterations (no intervention)
- Original intervention uses 10 iterations (intervention enabled)
- The control (10 iter, no intervention) partially controls for extra iterations

This script runs the cleaner comparison:
- Condition A: 8 iterations + intervention (matched to baseline iteration count)
- Condition B: 8 iterations + NO intervention (true matched control)

This isolates the intervention effect at the SAME iteration count as baseline,
eliminating the confound entirely.

Budget: $2 max. Uses GPT-4o-mini.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from datasets import load_dataset
from openai import OpenAI

from agenttelemetry.core.tracer import AgentTelemetryProvider
from agenttelemetry.core.privacy import PrivacyLevel
from agenttelemetry.core.spans import (
    AGENT_FRAMEWORK, AGENT_NAME, AGENT_TASK,
    LLM_COST, LLM_INPUT_TOKENS, LLM_LATENCY_MS, LLM_MODEL,
    LLM_OUTPUT_TOKENS, LLM_PROVIDER, LLM_TOTAL_TOKENS,
    MEMORY_KEY, MEMORY_OPERATION,
    PLANNING_STEP_COUNT, PLANNING_STRATEGY,
    REASONING_CHAIN,
    TOOL_INPUT, TOOL_NAME, TOOL_OUTPUT, TOOL_STATUS,
    AgentSpanKind, estimate_cost, start_agent_span,
)

from swebench_case_study import (
    SYSTEM_PROMPT, TOOL_SPECS, _extract_repo_context, execute_tool,
)
from swebench_closed_loop import (
    INTERVENTION_PROMPT, detect_reasoning_loop, run_improved_agent,
)

RESULTS_DIR = PROJECT_ROOT / "results" / "swebench_matched_control"
TRACES_DIR = RESULTS_DIR / "traces"


def run_agent_no_intervention(
    client: OpenAI,
    instance: Dict,
    tracer=None,
    model: str = "gpt-4o-mini",
    max_iterations: int = 8,
) -> Dict[str, Any]:
    """Run agent with NO intervention (pure matched control at 8 iterations).

    This is essentially the same as baseline but re-run fresh (not cached)
    to provide a proper contemporary control.
    """
    instance_id = instance["instance_id"]
    problem = instance["problem_statement"]
    repo = instance["repo"]
    repo_context = _extract_repo_context(instance)

    result = {
        "instance_id": instance_id,
        "repo": repo,
        "tool_calls": [],
        "iterations": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "proposed_patch": False,
        "verified": False,
        "error": None,
        "answer": "",
        "condition": "control_8iter",
    }

    with start_agent_span(
        name=f"swebench_control_8({instance_id})",
        kind=AgentSpanKind.AGENT,
        tracer=tracer,
        attributes={
            AGENT_NAME: "swebench_control_8iter",
            AGENT_FRAMEWORK: "agenttelemetry_matched_control",
            AGENT_TASK: f"{repo}: {problem[:200]}",
        },
    ):
        with start_agent_span(
            name="plan_diagnosis",
            kind=AgentSpanKind.PLANNING,
            tracer=tracer,
            attributes={
                PLANNING_STRATEGY: "diagnose_then_fix",
                PLANNING_STEP_COUNT: max_iterations,
            },
        ):
            pass

        with start_agent_span(
            name="load_context",
            kind=AgentSpanKind.MEMORY,
            tracer=tracer,
            attributes={
                MEMORY_OPERATION: "read",
                MEMORY_KEY: f"repo_context:{repo}",
            },
        ):
            pass

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Repository: {repo}\n\nBug Report:\n{problem[:3000]}"},
        ]

        try:
            for iteration in range(max_iterations):
                result["iterations"] = iteration + 1

                with start_agent_span(
                    name=f"reasoning_step_{iteration + 1}",
                    kind=AgentSpanKind.REASONING,
                    tracer=tracer,
                    attributes={
                        REASONING_CHAIN: f"Step {iteration + 1}: control (no intervention)",
                    },
                ):
                    pass

                start_time = time.time()
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOL_SPECS,
                    max_tokens=2048,
                )
                latency_ms = (time.time() - start_time) * 1000

                choice = response.choices[0]
                usage = response.usage
                result["total_input_tokens"] += usage.prompt_tokens
                result["total_output_tokens"] += usage.completion_tokens

                cost = estimate_cost(model, usage.prompt_tokens, usage.completion_tokens)

                with start_agent_span(
                    name=f"llm_call({model})",
                    kind=AgentSpanKind.LLM_CALL,
                    tracer=tracer,
                    attributes={
                        LLM_MODEL: model,
                        LLM_PROVIDER: "openai",
                        LLM_INPUT_TOKENS: usage.prompt_tokens,
                        LLM_OUTPUT_TOKENS: usage.completion_tokens,
                        LLM_TOTAL_TOKENS: usage.total_tokens,
                        LLM_COST: cost,
                        LLM_LATENCY_MS: latency_ms,
                    },
                ):
                    pass

                if not choice.message.tool_calls:
                    result["answer"] = choice.message.content or ""
                    break

                assistant_msg = {
                    "role": "assistant",
                    "content": choice.message.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in choice.message.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    tool_result = execute_tool(tc.function.name, args, repo_context, tracer)
                    result["tool_calls"].append(tc.function.name)

                    if tc.function.name == "propose_patch":
                        result["proposed_patch"] = True
                    if tc.function.name == "verify_fix":
                        result["verified"] = True

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    })

            else:
                result["error"] = "max_iterations_reached"

        except Exception as e:
            result["error"] = str(e)

        with start_agent_span(
            name="save_result",
            kind=AgentSpanKind.MEMORY,
            tracer=tracer,
            attributes={
                MEMORY_OPERATION: "write",
                MEMORY_KEY: f"result:{instance_id}",
            },
        ):
            pass

    return result


def main():
    """Run matched-iteration control experiment."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Matched-Iteration Control Experiment")
    print("Isolating intervention effect at identical iteration count (8)")
    print("=" * 70)

    # Load baseline results to identify the 24 failed instances
    baseline_path = PROJECT_ROOT / "results" / "swebench_case_study" / "agent_results.json"
    with open(baseline_path) as f:
        baseline_results = json.load(f)

    failed_instances = [r for r in baseline_results if r.get("error") == "max_iterations_reached"]
    succeeded_instances = [r for r in baseline_results if r.get("proposed_patch") and not r.get("error")]

    print(f"\nOriginal baseline (8 iterations, no intervention):")
    print(f"  Total: {len(baseline_results)}")
    print(f"  Patches proposed: {len(succeeded_instances)} ({len(succeeded_instances)/len(baseline_results)*100:.0f}%)")
    print(f"  Failed (max iter): {len(failed_instances)} ({len(failed_instances)/len(baseline_results)*100:.0f}%)")

    # Load SWE-bench dataset
    print("\nLoading SWE-bench Lite dataset...")
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    ds_by_id = {inst["instance_id"]: inst for inst in ds}

    failed_ids = [r["instance_id"] for r in failed_instances]

    client = OpenAI()
    total_cost = 0.0

    # ----------------------------------------------------------------
    # Condition A: 8 iterations + intervention (matched to baseline)
    # ----------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("CONDITION A: 8 iterations + INTERVENTION")
    print("=" * 70)

    provider_a = AgentTelemetryProvider(
        service_name="swebench_matched_intervention",
        privacy_level=PrivacyLevel.FULL,
    )
    exporter_a = provider_a.add_json_exporter(str(TRACES_DIR / "intervention_8iter_traces.jsonl"))
    provider_a.setup(set_global=True)
    tracer_a = provider_a.get_tracer("matched_intervention")

    intervention_results = []

    for idx, instance_id in enumerate(failed_ids):
        if instance_id not in ds_by_id:
            print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id}: SKIP (not in dataset)")
            continue

        instance = ds_by_id[instance_id]
        print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id[:50]}...", end=" ", flush=True)

        try:
            # Use run_improved_agent but with max_iterations=8
            result = run_improved_agent(
                client, instance, tracer=tracer_a, model="gpt-4o-mini",
                max_iterations=8,
            )
            result["condition"] = "intervention_8iter"
            intervention_results.append(result)

            cost = estimate_cost(
                "gpt-4o-mini",
                result["total_input_tokens"],
                result["total_output_tokens"],
            )
            total_cost += cost

            patch = "PATCH" if result["proposed_patch"] else "NO_PATCH"
            verified = "+VERIFIED" if result["verified"] else ""
            interventions = f" [{result.get('interventions', 0)} intv]" if result.get("interventions", 0) > 0 else ""
            err = f" ERR:{result['error'][:15]}" if result.get("error") else ""
            print(f"{patch}{verified} ({result['iterations']}it){interventions}{err}")

        except Exception as e:
            print(f"CRASH: {e}")
            intervention_results.append({
                "instance_id": instance_id,
                "error": str(e),
                "tool_calls": [],
                "iterations": 0,
                "proposed_patch": False,
                "condition": "intervention_8iter",
            })

        time.sleep(0.2)

        if total_cost > 2.0:
            print(f"\n  Budget guard: ${total_cost:.2f}")
            break

    provider_a.shutdown()

    # ----------------------------------------------------------------
    # Condition B: 8 iterations + NO intervention (true matched control)
    # ----------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("CONDITION B: 8 iterations + NO intervention (matched control)")
    print("=" * 70)

    provider_b = AgentTelemetryProvider(
        service_name="swebench_matched_control",
        privacy_level=PrivacyLevel.FULL,
    )
    exporter_b = provider_b.add_json_exporter(str(TRACES_DIR / "control_8iter_traces.jsonl"))
    provider_b.setup(set_global=True)
    tracer_b = provider_b.get_tracer("matched_control")

    control_results = []

    for idx, instance_id in enumerate(failed_ids):
        if instance_id not in ds_by_id:
            print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id}: SKIP (not in dataset)")
            continue

        # Budget check
        if total_cost > 2.0:
            print(f"\n  Budget guard: ${total_cost:.2f}")
            break

        instance = ds_by_id[instance_id]
        print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id[:50]}...", end=" ", flush=True)

        try:
            result = run_agent_no_intervention(
                client, instance, tracer=tracer_b, model="gpt-4o-mini",
                max_iterations=8,
            )
            control_results.append(result)

            cost = estimate_cost(
                "gpt-4o-mini",
                result["total_input_tokens"],
                result["total_output_tokens"],
            )
            total_cost += cost

            patch = "PATCH" if result["proposed_patch"] else "NO_PATCH"
            verified = "+VERIFIED" if result["verified"] else ""
            err = f" ERR:{result['error'][:15]}" if result.get("error") else ""
            print(f"{patch}{verified} ({result['iterations']}it){err}")

        except Exception as e:
            print(f"CRASH: {e}")
            control_results.append({
                "instance_id": instance_id,
                "error": str(e),
                "tool_calls": [],
                "iterations": 0,
                "proposed_patch": False,
                "condition": "control_8iter",
            })

        time.sleep(0.2)

    provider_b.shutdown()

    # ----------------------------------------------------------------
    # Analysis
    # ----------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("MATCHED-ITERATION RESULTS (all at 8 iterations)")
    print("=" * 70)

    # Ensure we compare same instance sets
    intervention_ids = {r["instance_id"] for r in intervention_results}
    control_ids = {r["instance_id"] for r in control_results}
    common_ids = intervention_ids & control_ids

    intv_common = [r for r in intervention_results if r["instance_id"] in common_ids]
    ctrl_common = [r for r in control_results if r["instance_id"] in common_ids]

    intv_recovered = [r for r in intv_common if r.get("proposed_patch")]
    ctrl_recovered = [r for r in ctrl_common if r.get("proposed_patch")]
    intv_interventions = [r for r in intv_common if r.get("interventions", 0) > 0]

    n_common = len(common_ids)
    n_total = len(baseline_results)

    print(f"\n  Instances compared: {n_common} (of {len(failed_ids)} failed)")

    print(f"\n  CONTROL (8 iter, no intervention):")
    print(f"    Recovery: {len(ctrl_recovered)}/{n_common} ({len(ctrl_recovered)/max(n_common,1)*100:.1f}%)")
    ctrl_combined = len(succeeded_instances) + len(ctrl_recovered)
    ctrl_rate = ctrl_combined / n_total * 100
    print(f"    Combined patch rate: {ctrl_combined}/{n_total} ({ctrl_rate:.1f}%)")

    print(f"\n  INTERVENTION (8 iter + loop detection):")
    print(f"    Recovery: {len(intv_recovered)}/{n_common} ({len(intv_recovered)/max(n_common,1)*100:.1f}%)")
    print(f"    Interventions triggered: {len(intv_interventions)}")
    intv_combined = len(succeeded_instances) + len(intv_recovered)
    intv_rate = intv_combined / n_total * 100
    print(f"    Combined patch rate: {intv_combined}/{n_total} ({intv_rate:.1f}%)")

    improvement_pp = intv_rate - ctrl_rate
    print(f"\n  IMPROVEMENT (intervention vs control at 8 iter):")
    print(f"    +{improvement_pp:.1f} percentage points")
    print(f"    Recovery lift: {len(intv_recovered) - len(ctrl_recovered)} additional instances")

    print(f"\n  Total cost: ${total_cost:.4f}")

    # Save results
    summary = {
        "experiment": "matched_iteration_control",
        "description": "Both conditions run at 8 iterations to eliminate iteration confound",
        "baseline_original": {
            "total": n_total,
            "patches": len(succeeded_instances),
            "patch_rate_pct": len(succeeded_instances) / n_total * 100,
            "iterations": 8,
        },
        "control_8iter": {
            "instances_run": len(ctrl_common),
            "recovered": len(ctrl_recovered),
            "recovery_rate_pct": len(ctrl_recovered) / max(n_common, 1) * 100,
            "combined_patches": ctrl_combined,
            "combined_rate_pct": ctrl_rate,
        },
        "intervention_8iter": {
            "instances_run": len(intv_common),
            "recovered": len(intv_recovered),
            "recovery_rate_pct": len(intv_recovered) / max(n_common, 1) * 100,
            "interventions_triggered": len(intv_interventions),
            "combined_patches": intv_combined,
            "combined_rate_pct": intv_rate,
        },
        "improvement_pp": improvement_pp,
        "cost_usd": total_cost,
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    with open(RESULTS_DIR / "intervention_results.json", "w") as f:
        json.dump(intervention_results, f, indent=2, default=str)

    with open(RESULTS_DIR / "control_results.json", "w") as f:
        json.dump(control_results, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print("MATCHED-ITERATION EXPERIMENT COMPLETE")
    print(f"Results: {RESULTS_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
