"""Multi-seed SWE-bench closed-loop experiment.

Adds statistical rigor to the closed-loop improvement result:
1. Re-runs the 24 failed instances 2 MORE times with intervention (seeds 2 & 3)
   using temperature 0.3 and 0.7 respectively to introduce variation.
2. Runs a NO-INTERVENTION CONTROL: same 24 instances, 10 iterations,
   temperature=0, but WITHOUT reasoning-loop intervention.
   This isolates the intervention effect from the extra-iterations effect.
3. Computes mean +/- std for patch rate across the 3 intervention runs.
4. Compares intervention vs control.

Seed 1 (already done): improved_results.json (temperature=0 default)
Seed 2: temperature=0.3 with intervention
Seed 3: temperature=0.7 with intervention
Control: temperature=0, 10 iterations, NO intervention
"""

from __future__ import annotations

import json
import os
import sys
import time
import math
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

RESULTS_DIR = PROJECT_ROOT / "results" / "swebench_multi_seed"

# ── Intervention prompt (same as closed-loop experiment) ──
INTERVENTION_PROMPT = """IMPORTANT: You appear to be stuck in a repetitive search loop. You have searched for similar terms multiple times without making progress.

CHANGE YOUR STRATEGY:
1. STOP searching for the same patterns
2. Instead, try ONE of these approaches:
   - Read a specific file you already found (use read_file)
   - Analyze the error message directly (use analyze_error)
   - Based on what you've found so far, propose a patch (use propose_patch)
   - Try a completely different search query with different keywords

Do NOT repeat the same search_code calls. Take a different action NOW."""


def detect_reasoning_loop(tool_history: List[str], window: int = 3) -> bool:
    """Detect if the agent is stuck in a reasoning loop."""
    if len(tool_history) < window:
        return False
    recent = tool_history[-window:]
    if len(set(recent)) == 1 and recent[0] == "search_code":
        return True
    return False


def run_agent(
    client: OpenAI,
    instance: Dict,
    tracer=None,
    model: str = "gpt-4o-mini",
    max_iterations: int = 10,
    temperature: float = 0.0,
    enable_intervention: bool = True,
    seed_label: str = "seed1",
) -> Dict[str, Any]:
    """Run agent on a single SWE-bench instance.

    Args:
        enable_intervention: If True, inject strategy-change prompt on reasoning loops.
                           If False, run with same iteration budget but no intervention (control).
        temperature: LLM temperature for variation across seeds.
        seed_label: Label for tracing/logging.
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
        "interventions": 0,
        "intervention_at": [],
        "seed": seed_label,
        "temperature": temperature,
        "enable_intervention": enable_intervention,
    }

    agent_name = "swebench_intervention" if enable_intervention else "swebench_control"

    with start_agent_span(
        name=f"{agent_name}({instance_id})",
        kind=AgentSpanKind.AGENT,
        tracer=tracer,
        attributes={
            AGENT_NAME: agent_name,
            AGENT_FRAMEWORK: f"agenttelemetry_multi_seed_{seed_label}",
            AGENT_TASK: f"{repo}: {problem[:200]}",
        },
    ):
        with start_agent_span(
            name="plan",
            kind=AgentSpanKind.PLANNING,
            tracer=tracer,
            attributes={
                PLANNING_STRATEGY: "diagnose_then_fix" + ("_with_intervention" if enable_intervention else "_control"),
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

                # Telemetry-guided intervention (only if enabled)
                if enable_intervention and detect_reasoning_loop(result["tool_calls"], window=3):
                    result["interventions"] += 1
                    result["intervention_at"].append(iteration)

                    from agenttelemetry.core.spans import GUARDRAIL_NAME, GUARDRAIL_RESULT
                    with start_agent_span(
                        name="reasoning_loop_intervention",
                        kind=AgentSpanKind.GUARD_RAIL,
                        tracer=tracer,
                        attributes={
                            GUARDRAIL_NAME: "reasoning_loop_detector",
                            GUARDRAIL_RESULT: "INTERVENTION_TRIGGERED",
                        },
                    ):
                        pass

                    messages.append({
                        "role": "user",
                        "content": INTERVENTION_PROMPT,
                    })

                # REASONING span
                with start_agent_span(
                    name=f"reasoning_step_{iteration + 1}",
                    kind=AgentSpanKind.REASONING,
                    tracer=tracer,
                    attributes={
                        REASONING_CHAIN: f"Step {iteration + 1} [{seed_label}]",
                    },
                ):
                    pass

                # LLM call (with temperature)
                start_time = time.time()
                create_kwargs = dict(
                    model=model,
                    messages=messages,
                    tools=TOOL_SPECS,
                    max_tokens=2048,
                )
                if temperature > 0:
                    create_kwargs["temperature"] = temperature

                response = client.chat.completions.create(**create_kwargs)
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
                MEMORY_KEY: f"result:{instance_id}:{seed_label}",
            },
        ):
            pass

    return result


def run_condition(
    client: OpenAI,
    ds_by_id: Dict,
    failed_ids: List[str],
    tracer,
    label: str,
    temperature: float,
    enable_intervention: bool,
    budget_remaining: float,
) -> tuple[List[Dict], float]:
    """Run a single experimental condition across all failed instances."""
    results = []
    total_cost = 0.0

    print(f"\n{'─' * 60}")
    print(f"  Condition: {label}")
    print(f"  temperature={temperature}, intervention={'ON' if enable_intervention else 'OFF'}")
    print(f"  Budget remaining: ${budget_remaining:.2f}")
    print(f"{'─' * 60}")

    for idx, instance_id in enumerate(failed_ids):
        if instance_id not in ds_by_id:
            print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id}: SKIP (not in dataset)")
            continue

        instance = ds_by_id[instance_id]
        print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id[:50]}...", end=" ", flush=True)

        try:
            result = run_agent(
                client, instance,
                tracer=tracer,
                model="gpt-4o-mini",
                max_iterations=10,
                temperature=temperature,
                enable_intervention=enable_intervention,
                seed_label=label,
            )
            results.append(result)
            cost = estimate_cost(
                "gpt-4o-mini",
                result["total_input_tokens"],
                result["total_output_tokens"],
            )
            total_cost += cost

            patch = "PATCH" if result["proposed_patch"] else "NO_PATCH"
            verified = "+V" if result["verified"] else ""
            intv = f" [{result['interventions']}intv]" if result["interventions"] > 0 else ""
            err = f" ERR:{result['error'][:15]}" if result.get("error") else ""
            print(f"{patch}{verified} ({result['iterations']}it){intv}{err}")

        except Exception as e:
            print(f"CRASH: {e}")
            results.append({
                "instance_id": instance_id,
                "error": str(e),
                "tool_calls": [],
                "iterations": 0,
                "proposed_patch": False,
                "verified": False,
                "seed": label,
                "temperature": temperature,
                "enable_intervention": enable_intervention,
            })

        time.sleep(0.2)

        if total_cost > budget_remaining:
            print(f"\n  Budget guard: ${total_cost:.2f} spent in this condition, stopping")
            break

    return results, total_cost


def compute_stats(values: List[float]) -> Dict[str, float]:
    """Compute mean, std, min, max for a list of values."""
    n = len(values)
    if n == 0:
        return {"mean": 0, "std": 0, "min": 0, "max": 0, "n": 0}
    mean = sum(values) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)  # sample std
        std = math.sqrt(variance)
    else:
        std = 0.0
    return {
        "mean": round(mean, 2),
        "std": round(std, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "n": n,
    }


def main():
    """Run multi-seed closed-loop experiment."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    traces_dir = RESULTS_DIR / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Multi-Seed Closed-Loop Experiment")
    print("Statistical rigor: 3 seeds + no-intervention control")
    print("=" * 70)

    # ── Load baseline results to get the 24 failed instance IDs ──
    baseline_path = PROJECT_ROOT / "results" / "swebench_case_study" / "agent_results.json"
    with open(baseline_path) as f:
        baseline_results = json.load(f)

    failed_instances = [r for r in baseline_results if r.get("error") == "max_iterations_reached"]
    succeeded_instances = [r for r in baseline_results if r.get("proposed_patch") and not r.get("error")]
    failed_ids = [r["instance_id"] for r in failed_instances]

    n_baseline = len(baseline_results)
    n_baseline_success = len(succeeded_instances)
    baseline_patch_rate = n_baseline_success / n_baseline * 100

    print(f"\nBaseline: {n_baseline_success}/{n_baseline} = {baseline_patch_rate:.1f}% patch rate")
    print(f"Failed instances to re-run: {len(failed_ids)}")

    # ── Load seed 1 results (already done) ──
    seed1_path = PROJECT_ROOT / "results" / "swebench_closed_loop" / "improved_results.json"
    with open(seed1_path) as f:
        seed1_results = json.load(f)
    seed1_patches = len([r for r in seed1_results if r.get("proposed_patch")])
    print(f"Seed 1 (loaded): {seed1_patches}/{len(seed1_results)} recovered patches (temperature=0)")

    # ── Load SWE-bench dataset ──
    print("\nLoading SWE-bench Lite dataset...")
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    ds_by_id = {inst["instance_id"]: inst for inst in ds}
    print(f"  {len(ds)} instances available")

    # ── Setup ──
    client = OpenAI()
    provider = AgentTelemetryProvider(
        service_name="swebench_multi_seed",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(str(traces_dir / "multi_seed_traces.jsonl"))
    provider.setup(set_global=True)
    tracer = provider.get_tracer("multi_seed")

    TOTAL_BUDGET = 3.0
    total_spent = 0.0
    all_condition_results = {}

    # ── Condition 1: Seed 2 (intervention, temperature=0.3) ──
    seed2_results, seed2_cost = run_condition(
        client, ds_by_id, failed_ids, tracer,
        label="seed2_intervention_t0.3",
        temperature=0.3,
        enable_intervention=True,
        budget_remaining=TOTAL_BUDGET - total_spent,
    )
    total_spent += seed2_cost
    all_condition_results["seed2"] = seed2_results

    # ── Condition 2: Seed 3 (intervention, temperature=0.7) ──
    seed3_results, seed3_cost = run_condition(
        client, ds_by_id, failed_ids, tracer,
        label="seed3_intervention_t0.7",
        temperature=0.7,
        enable_intervention=True,
        budget_remaining=TOTAL_BUDGET - total_spent,
    )
    total_spent += seed3_cost
    all_condition_results["seed3"] = seed3_results

    # ── Condition 3: Control (no intervention, temperature=0, 10 iterations) ──
    control_results, control_cost = run_condition(
        client, ds_by_id, failed_ids, tracer,
        label="control_no_intervention_t0",
        temperature=0.0,
        enable_intervention=False,
        budget_remaining=TOTAL_BUDGET - total_spent,
    )
    total_spent += control_cost
    all_condition_results["control"] = control_results

    provider.shutdown()

    # ── Analysis ──
    print(f"\n{'=' * 70}")
    print("MULTI-SEED RESULTS")
    print("=" * 70)

    # Count recovered patches per condition
    seed1_recovered = seed1_patches
    seed2_recovered = len([r for r in seed2_results if r.get("proposed_patch")])
    seed3_recovered = len([r for r in seed3_results if r.get("proposed_patch")])
    control_recovered = len([r for r in control_results if r.get("proposed_patch")])

    n_failed = len(failed_ids)

    # Recovery rates (of the 24 failed instances)
    seed1_recovery_rate = seed1_recovered / n_failed * 100 if n_failed > 0 else 0
    seed2_recovery_rate = seed2_recovered / n_failed * 100 if n_failed > 0 else 0
    seed3_recovery_rate = seed3_recovered / n_failed * 100 if n_failed > 0 else 0
    control_recovery_rate = control_recovered / n_failed * 100 if n_failed > 0 else 0

    # Combined patch rates (original successes + newly recovered)
    seed1_combined = (n_baseline_success + seed1_recovered) / n_baseline * 100
    seed2_combined = (n_baseline_success + seed2_recovered) / n_baseline * 100
    seed3_combined = (n_baseline_success + seed3_recovered) / n_baseline * 100
    control_combined = (n_baseline_success + control_recovered) / n_baseline * 100

    intervention_recovery_rates = [seed1_recovery_rate, seed2_recovery_rate, seed3_recovery_rate]
    intervention_combined_rates = [seed1_combined, seed2_combined, seed3_combined]

    recovery_stats = compute_stats(intervention_recovery_rates)
    combined_stats = compute_stats(intervention_combined_rates)

    print(f"\n  Baseline patch rate: {n_baseline_success}/{n_baseline} = {baseline_patch_rate:.1f}%")
    print(f"  Failed instances: {n_failed}")

    print(f"\n  ── Per-Seed Recovery (of {n_failed} failed instances) ──")
    print(f"  Seed 1 (t=0.0, intervention): {seed1_recovered}/{n_failed} = {seed1_recovery_rate:.1f}%")
    print(f"  Seed 2 (t=0.3, intervention): {seed2_recovered}/{n_failed} = {seed2_recovery_rate:.1f}%")
    print(f"  Seed 3 (t=0.7, intervention): {seed3_recovered}/{n_failed} = {seed3_recovery_rate:.1f}%")
    print(f"  Control (t=0.0, NO interv.):  {control_recovered}/{n_failed} = {control_recovery_rate:.1f}%")

    print(f"\n  ── Intervention Recovery Stats (3 seeds) ──")
    print(f"  Mean: {recovery_stats['mean']:.1f}% +/- {recovery_stats['std']:.1f}%")
    print(f"  Range: [{recovery_stats['min']:.1f}%, {recovery_stats['max']:.1f}%]")

    print(f"\n  ── Combined Patch Rate (baseline + recovered) ──")
    print(f"  Seed 1: {n_baseline_success + seed1_recovered}/{n_baseline} = {seed1_combined:.1f}%")
    print(f"  Seed 2: {n_baseline_success + seed2_recovered}/{n_baseline} = {seed2_combined:.1f}%")
    print(f"  Seed 3: {n_baseline_success + seed3_recovered}/{n_baseline} = {seed3_combined:.1f}%")
    print(f"  Control: {n_baseline_success + control_recovered}/{n_baseline} = {control_combined:.1f}%")
    print(f"  Intervention mean: {combined_stats['mean']:.1f}% +/- {combined_stats['std']:.1f}%")

    # Improvement over control
    improvement_over_control = combined_stats["mean"] - control_combined
    recovery_improvement = recovery_stats["mean"] - control_recovery_rate

    print(f"\n  ── Intervention vs Control ──")
    print(f"  Intervention recovery (mean): {recovery_stats['mean']:.1f}%")
    print(f"  Control recovery:             {control_recovery_rate:.1f}%")
    print(f"  Difference:                   +{recovery_improvement:.1f} pp")
    print(f"\n  Intervention combined (mean): {combined_stats['mean']:.1f}%")
    print(f"  Control combined:             {control_combined:.1f}%")
    print(f"  Difference:                   +{improvement_over_control:.1f} pp")

    # Interventions triggered per seed
    seed1_intv = len([r for r in seed1_results if r.get("interventions", 0) > 0])
    seed2_intv = len([r for r in seed2_results if r.get("interventions", 0) > 0])
    seed3_intv = len([r for r in seed3_results if r.get("interventions", 0) > 0])
    print(f"\n  ── Interventions Triggered ──")
    print(f"  Seed 1: {seed1_intv}/{len(seed1_results)} instances")
    print(f"  Seed 2: {seed2_intv}/{len(seed2_results)} instances")
    print(f"  Seed 3: {seed3_intv}/{len(seed3_results)} instances")
    print(f"  Control: 0/{len(control_results)} (disabled)")

    print(f"\n  ── Cost ──")
    print(f"  Seed 2: ${seed2_cost:.4f}")
    print(f"  Seed 3: ${seed3_cost:.4f}")
    print(f"  Control: ${control_cost:.4f}")
    print(f"  Total this run: ${total_spent:.4f}")

    # ── Save results ──
    summary = {
        "experiment": "multi_seed_closed_loop",
        "baseline": {
            "total_instances": n_baseline,
            "patches_proposed": n_baseline_success,
            "patch_rate_pct": round(baseline_patch_rate, 2),
            "failed_instances": n_failed,
        },
        "intervention_seeds": {
            "seed1": {
                "label": "seed1_intervention_t0.0",
                "temperature": 0.0,
                "recovered": seed1_recovered,
                "recovery_rate_pct": round(seed1_recovery_rate, 2),
                "combined_patch_rate_pct": round(seed1_combined, 2),
                "interventions_triggered": seed1_intv,
                "source": "pre-existing (improved_results.json)",
            },
            "seed2": {
                "label": "seed2_intervention_t0.3",
                "temperature": 0.3,
                "recovered": seed2_recovered,
                "recovery_rate_pct": round(seed2_recovery_rate, 2),
                "combined_patch_rate_pct": round(seed2_combined, 2),
                "interventions_triggered": seed2_intv,
                "n_instances_run": len(seed2_results),
                "cost": round(seed2_cost, 4),
            },
            "seed3": {
                "label": "seed3_intervention_t0.7",
                "temperature": 0.7,
                "recovered": seed3_recovered,
                "recovery_rate_pct": round(seed3_recovery_rate, 2),
                "combined_patch_rate_pct": round(seed3_combined, 2),
                "interventions_triggered": seed3_intv,
                "n_instances_run": len(seed3_results),
                "cost": round(seed3_cost, 4),
            },
        },
        "intervention_stats": {
            "recovery_rate": recovery_stats,
            "combined_patch_rate": combined_stats,
        },
        "control": {
            "label": "control_no_intervention_t0",
            "temperature": 0.0,
            "enable_intervention": False,
            "recovered": control_recovered,
            "recovery_rate_pct": round(control_recovery_rate, 2),
            "combined_patch_rate_pct": round(control_combined, 2),
            "n_instances_run": len(control_results),
            "cost": round(control_cost, 4),
        },
        "comparison": {
            "intervention_recovery_mean_pct": round(recovery_stats["mean"], 2),
            "control_recovery_pct": round(control_recovery_rate, 2),
            "recovery_improvement_pp": round(recovery_improvement, 2),
            "intervention_combined_mean_pct": round(combined_stats["mean"], 2),
            "control_combined_pct": round(control_combined, 2),
            "combined_improvement_pp": round(improvement_over_control, 2),
        },
        "total_cost": round(total_spent, 4),
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    with open(RESULTS_DIR / "seed2_results.json", "w") as f:
        json.dump(seed2_results, f, indent=2, default=str)

    with open(RESULTS_DIR / "seed3_results.json", "w") as f:
        json.dump(seed3_results, f, indent=2, default=str)

    with open(RESULTS_DIR / "control_results.json", "w") as f:
        json.dump(control_results, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print("MULTI-SEED EXPERIMENT COMPLETE")
    print(f"Results: {RESULTS_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
