"""Closed-loop improvement experiment for SWE-bench.

Demonstrates that AgentTelemetry's fault detection is ACTIONABLE:
1. Run baseline agent on SWE-bench (already done — 33% patch rate)
2. Add telemetry-guided intervention: when reasoning-loop detected mid-run,
   inject a strategy-change prompt
3. Re-run the 24 failed instances with the intervention
4. Measure improvement in patch rate

This closes the loop: observability → diagnosis → fix → improvement.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# Add experiments to path
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

RESULTS_DIR = PROJECT_ROOT / "results" / "swebench_closed_loop"
TRACES_DIR = RESULTS_DIR / "traces"

# The intervention prompt injected when reasoning loop is detected
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
    """Detect if the agent is stuck in a reasoning loop.

    Returns True if the last `window` tool calls are all the same tool
    with no progress (all search_code or all the same tool).
    """
    if len(tool_history) < window:
        return False

    recent = tool_history[-window:]
    # All same tool = likely stuck
    if len(set(recent)) == 1 and recent[0] == "search_code":
        return True
    return False


def run_improved_agent(
    client: OpenAI,
    instance: Dict,
    tracer=None,
    model: str = "gpt-4o-mini",
    max_iterations: int = 10,  # More iterations since we intervene
) -> Dict[str, Any]:
    """Run agent with telemetry-guided intervention on reasoning loops."""
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
    }

    with start_agent_span(
        name=f"swebench_improved({instance_id})",
        kind=AgentSpanKind.AGENT,
        tracer=tracer,
        attributes={
            AGENT_NAME: "swebench_improved_agent",
            AGENT_FRAMEWORK: "agenttelemetry_swebench_closed_loop",
            AGENT_TASK: f"{repo}: {problem[:200]}",
        },
    ):
        # PLANNING span
        with start_agent_span(
            name="plan_with_intervention",
            kind=AgentSpanKind.PLANNING,
            tracer=tracer,
            attributes={
                PLANNING_STRATEGY: "diagnose_then_fix_with_loop_detection",
                PLANNING_STEP_COUNT: max_iterations,
            },
        ):
            pass

        # MEMORY span
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

                # --- TELEMETRY-GUIDED INTERVENTION ---
                chain_label = "normal"
                # Check for reasoning loop using tool call history
                if detect_reasoning_loop(result["tool_calls"], window=3):
                    result["interventions"] += 1
                    result["intervention_at"].append(iteration)

                    # Record intervention as a GUARD_RAIL span
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

                    # Inject strategy-change prompt
                    messages.append({
                        "role": "user",
                        "content": INTERVENTION_PROMPT,
                    })

                    post_intervention = result["interventions"] > 0 and result["intervention_at"] and iteration == result["intervention_at"][-1]
                    chain_label = "POST-INTERVENTION" if post_intervention else "normal"

                # REASONING span
                with start_agent_span(
                    name=f"reasoning_step_{iteration + 1}",
                    kind=AgentSpanKind.REASONING,
                    tracer=tracer,
                    attributes={
                        REASONING_CHAIN: f"Step {iteration + 1}: {chain_label}",
                    },
                ):
                    pass

                # LLM call
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

                # Process tool calls
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

        # MEMORY span (write)
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
    """Run closed-loop improvement experiment."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Closed-Loop Improvement Experiment")
    print("Telemetry-guided intervention for reasoning loops")
    print("=" * 70)

    # Load baseline results to identify failed instances
    baseline_path = PROJECT_ROOT / "results" / "swebench_case_study" / "agent_results.json"
    with open(baseline_path) as f:
        baseline_results = json.load(f)

    failed_instances = [r for r in baseline_results if r.get("error") == "max_iterations_reached"]
    succeeded_instances = [r for r in baseline_results if r.get("proposed_patch") and not r.get("error")]

    print(f"\nBaseline results:")
    print(f"  Total: {len(baseline_results)}")
    print(f"  Patches proposed: {len(succeeded_instances)} ({len(succeeded_instances)/len(baseline_results)*100:.0f}%)")
    print(f"  Failed (reasoning loop): {len(failed_instances)} ({len(failed_instances)/len(baseline_results)*100:.0f}%)")

    # Load SWE-bench dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    ds_by_id = {inst["instance_id"]: inst for inst in ds}

    # Re-run only the failed instances with intervention
    failed_ids = [r["instance_id"] for r in failed_instances]

    client = OpenAI()
    provider = AgentTelemetryProvider(
        service_name="swebench_closed_loop",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(str(TRACES_DIR / "closed_loop_traces.jsonl"))
    provider.setup(set_global=True)
    tracer = provider.get_tracer("closed_loop")

    improved_results = []
    total_cost = 0.0

    print(f"\nRe-running {len(failed_ids)} failed instances with intervention...")
    print("-" * 70)

    for idx, instance_id in enumerate(failed_ids):
        if instance_id not in ds_by_id:
            print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id}: SKIP (not in dataset)")
            continue

        instance = ds_by_id[instance_id]
        print(f"  [{idx+1:>2}/{len(failed_ids)}] {instance_id[:50]}...", end=" ", flush=True)

        try:
            result = run_improved_agent(
                client, instance, tracer=tracer, model="gpt-4o-mini",
            )
            improved_results.append(result)
            total_cost += estimate_cost(
                "gpt-4o-mini",
                result["total_input_tokens"],
                result["total_output_tokens"],
            )

            patch = "PATCH" if result["proposed_patch"] else "NO_PATCH"
            verified = "+VERIFIED" if result["verified"] else ""
            interventions = f" [{result['interventions']} interventions]" if result["interventions"] > 0 else ""
            err = f" ERR:{result['error'][:15]}" if result.get("error") else ""
            print(f"{patch}{verified} ({result['iterations']}it){interventions}{err}")

        except Exception as e:
            print(f"CRASH: {e}")
            improved_results.append({
                "instance_id": instance_id,
                "error": str(e),
                "tool_calls": [],
                "iterations": 0,
                "proposed_patch": False,
            })

        time.sleep(0.2)

        if total_cost > 3.0:
            print(f"\n  Budget guard: ${total_cost:.2f}")
            break

    provider.shutdown()

    # Analysis
    print(f"\n{'=' * 70}")
    print("RESULTS COMPARISON")
    print("=" * 70)

    improved_patches = [r for r in improved_results if r.get("proposed_patch")]
    improved_verified = [r for r in improved_results if r.get("verified")]
    still_failed = [r for r in improved_results if r.get("error") == "max_iterations_reached"]
    had_intervention = [r for r in improved_results if r.get("interventions", 0) > 0]

    n_improved = len(improved_results)
    n_baseline = len(baseline_results)

    baseline_patch_rate = len(succeeded_instances) / n_baseline * 100

    # Combined: original successes + newly recovered
    total_patches = len(succeeded_instances) + len(improved_patches)
    improved_patch_rate = total_patches / n_baseline * 100

    print(f"\n  Baseline patch rate: {len(succeeded_instances)}/{n_baseline} = {baseline_patch_rate:.1f}%")
    print(f"  Improved patch rate: {total_patches}/{n_baseline} = {improved_patch_rate:.1f}%")
    print(f"  Improvement: +{improved_patch_rate - baseline_patch_rate:.1f} percentage points")
    print(f"\n  Of {len(failed_ids)} previously-failed instances:")
    print(f"    Recovered (now propose patch): {len(improved_patches)}")
    print(f"    Still failed: {len(still_failed)}")
    print(f"    Had intervention triggered: {len(had_intervention)}")
    print(f"\n  Cost: ${total_cost:.4f}")

    # Save
    summary = {
        "baseline": {
            "total": n_baseline,
            "patches": len(succeeded_instances),
            "patch_rate": baseline_patch_rate,
        },
        "improved": {
            "previously_failed": len(failed_ids),
            "recovered": len(improved_patches),
            "still_failed": len(still_failed),
            "interventions_triggered": len(had_intervention),
        },
        "combined": {
            "total": n_baseline,
            "patches": total_patches,
            "patch_rate": improved_patch_rate,
            "improvement_pp": improved_patch_rate - baseline_patch_rate,
        },
        "cost": total_cost,
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    with open(RESULTS_DIR / "improved_results.json", "w") as f:
        json.dump(improved_results, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print("CLOSED-LOOP EXPERIMENT COMPLETE")
    print(f"Results: {RESULTS_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
