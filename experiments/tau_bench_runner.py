"""τ-bench runner with AgentTelemetry intervention.

Replaces the SWE-bench Lite experiment that hit ceiling effects.
τ-bench retail has ~50% pass^1 baseline → measurable headroom.

Design: 2 providers × 115 retail tasks × 4 trials × 2 conditions = 1,840 cells

Usage:
    PYTHONPATH=external/tau-bench .venv/bin/python3.12 \\
        experiments/tau_bench_runner.py \\
        --provider anthropic --model claude-opus-4-7 \\
        --condition control --trials 4 --workers 8 \\
        --output-dir results/tau_bench/opus-control
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import comb
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TAU_BENCH = PROJECT_ROOT / "external" / "tau-bench"
sys.path.insert(0, str(TAU_BENCH))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from litellm import completion
from tau_bench.envs import get_env
from tau_bench.envs.user import UserStrategy
from tau_bench.types import SolveResult, Action, RESPOND_ACTION_NAME
from tau_bench.agents.tool_calling_agent import ToolCallingAgent, message_to_action


# ============================================================
# Statistics helpers (Fisher's exact, McNemar's)
# ============================================================

def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    n1, n2, k, N = a + b, c + d, a + c, a + b + c + d
    if N == 0:
        return 1.0

    def hg(x: int) -> float:
        if x < 0 or x > min(n1, k) or (k - x) > n2 or (k - x) < 0:
            return 0.0
        return comb(n1, x) * comb(n2, k - x) / comb(N, k)

    p_obs = hg(a)
    return sum(hg(x) for x in range(0, min(n1, k) + 1) if hg(x) <= p_obs + 1e-12)


def mcnemar_p(b: int, c: int) -> float:
    """McNemar's exact (binomial) two-sided p-value.

    b = control_pass & intervention_fail
    c = control_fail & intervention_pass
    """
    n = b + c
    if n == 0:
        return 1.0
    # Two-sided exact binomial test under H0: p=0.5
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * p)


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    from math import sqrt
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


# ============================================================
# Intervention: REASONING-loop detector + strategy-change prompt
# ============================================================

INTERVENTION_PROMPT = (
    "[OBSERVABILITY-DETECTED REASONING LOOP] You have called the same tool with "
    "essentially the same arguments 3 or more times consecutively without progress. "
    "STOP the current strategy. List 2 alternative approaches you have not tried, "
    "pick the most promising one, and execute it on your next step. Do not repeat "
    "the previous tool call."
)


class InstrumentedToolCallingAgent(ToolCallingAgent):
    """Drop-in for ToolCallingAgent with AgentTelemetry instrumentation.

    Tracks consecutive identical tool calls in the messages history and, if
    enable_intervention=True, injects a strategy-change prompt when the
    REASONING-loop detector fires.
    """

    def __init__(self, *args, enable_intervention: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_intervention = enable_intervention

    def solve(self, env, task_index=None, max_num_steps: int = 30) -> SolveResult:
        total_cost = 0.0
        env_reset_res = env.reset(task_index=task_index)
        obs = env_reset_res.observation
        info = env_reset_res.info.model_dump()
        reward = 0.0
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.wiki},
            {"role": "user", "content": obs},
        ]

        # Track consecutive identical tool calls
        recent_tool_calls: List[Tuple[str, str]] = []  # (tool_name, args_signature)
        intervention_fires = 0
        loop_detected_steps: List[int] = []

        for step_idx in range(max_num_steps):
            # Detect loop BEFORE making the call: if last 3 messages were tool calls
            # to the same tool with the same args, fire intervention before next step
            if (self.enable_intervention
                    and len(recent_tool_calls) >= 3
                    and recent_tool_calls[-1] == recent_tool_calls[-2] == recent_tool_calls[-3]):
                # Inject intervention into the message history
                messages.append({
                    "role": "user",
                    "content": INTERVENTION_PROMPT,
                })
                intervention_fires += 1
                loop_detected_steps.append(step_idx)
                # Reset the tracking so we don't fire again immediately on next identical call
                recent_tool_calls = []

            res = completion(
                messages=messages,
                model=self.model,
                custom_llm_provider=self.provider,
                tools=self.tools_info,
                temperature=self.temperature,
            )
            next_message = res.choices[0].message.model_dump()
            total_cost += res._hidden_params.get("response_cost", 0) or 0
            action = message_to_action(next_message)

            env_response = env.step(action)
            reward = env_response.reward
            info = {**info, **env_response.info.model_dump()}

            if action.name != RESPOND_ACTION_NAME:
                next_message["tool_calls"] = next_message["tool_calls"][:1]
                args_sig = json.dumps(action.kwargs, sort_keys=True)[:200]
                recent_tool_calls.append((action.name, args_sig))
                messages.extend([
                    next_message,
                    {
                        "role": "tool",
                        "tool_call_id": next_message["tool_calls"][0]["id"],
                        "name": next_message["tool_calls"][0]["function"]["name"],
                        "content": env_response.observation,
                    },
                ])
            else:
                # User response, not a tool call - reset tool tracking
                recent_tool_calls = []
                messages.extend([
                    next_message,
                    {"role": "user", "content": env_response.observation},
                ])

            if env_response.done:
                break

        result = SolveResult(
            reward=reward, info=info, messages=messages, total_cost=total_cost,
        )
        # Attach intervention telemetry as extra fields on the dict
        result_dict = result.model_dump()
        result_dict["intervention_fires"] = intervention_fires
        result_dict["loop_detected_steps"] = loop_detected_steps
        return result_dict


# ============================================================
# Per-task worker
# ============================================================

def run_one_task(
    task_idx: int, trial: int, condition: str,
    provider: str, model: str, user_provider: str, user_model: str,
    env_name: str, agent_strategy: str, temperature: float,
    output_dir: Path,
) -> Dict[str, Any]:
    """Run one task in one trial in one condition."""
    enable_intervention = (condition == "intervention")

    env = get_env(
        env_name,
        user_strategy="llm",
        user_model=user_model,
        user_provider=user_provider,
        task_split="test",
    )

    agent = InstrumentedToolCallingAgent(
        tools_info=env.tools_info, wiki=env.wiki,
        model=model, provider=provider, temperature=temperature,
        enable_intervention=enable_intervention,
    )

    start = time.time()
    err: Optional[str] = None
    try:
        result_dict = agent.solve(env, task_index=task_idx, max_num_steps=30)
    except Exception as e:
        result_dict = {
            "reward": 0.0, "info": {}, "messages": [], "total_cost": 0.0,
            "intervention_fires": 0, "loop_detected_steps": [],
        }
        err = f"{type(e).__name__}: {e}"
    elapsed = time.time() - start

    record = {
        "task_idx": task_idx, "trial": trial, "condition": condition,
        "provider": provider, "model": model, "env": env_name,
        "agent_strategy": agent_strategy, "temperature": temperature,
        "elapsed_s": elapsed, "error": err,
        "reward": result_dict["reward"],
        "info": result_dict["info"],
        "total_cost": result_dict["total_cost"],
        "intervention_fires": result_dict.get("intervention_fires", 0),
        "loop_detected_steps": result_dict.get("loop_detected_steps", []),
        "n_messages": len(result_dict.get("messages", [])),
        # PERSIST FULL MESSAGES - this is the fix for the SWE-bench data-loss bug
        "messages": result_dict.get("messages", []),
    }

    # Per-task file
    out_file = output_dir / "per_task" / f"task{task_idx}_trial{trial}_{condition}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(record, f, indent=2, default=str)

    return record


# ============================================================
# Main
# ============================================================

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--provider", required=True, choices=["openai", "anthropic"])
    p.add_argument("--model", required=True, help="e.g. claude-opus-4-7 or gpt-5.5")
    p.add_argument("--user-provider", default="openai")
    p.add_argument("--user-model", default="gpt-4o")
    p.add_argument("--env", default="retail", choices=["retail", "airline"])
    p.add_argument("--agent-strategy", default="tool-calling")
    p.add_argument("--trials", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--start-task", type=int, default=0)
    p.add_argument("--end-task", type=int, default=-1)  # -1 = all
    p.add_argument("--task-ids", type=int, nargs="+", default=None)
    p.add_argument("--conditions", nargs="+", default=["control", "intervention"])
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load tasks
    env = get_env(args.env, user_strategy="llm",
                  user_model=args.user_model, user_provider=args.user_provider,
                  task_split="test")
    n_total_tasks = len(env.tasks)
    if args.task_ids:
        task_ids = args.task_ids
    else:
        end = args.end_task if args.end_task != -1 else n_total_tasks
        task_ids = list(range(args.start_task, min(end, n_total_tasks)))

    # Build job list
    jobs = []
    for task_idx in task_ids:
        for trial in range(args.trials):
            for cond in args.conditions:
                jobs.append({
                    "task_idx": task_idx, "trial": trial, "condition": cond,
                })
    print(f"Loaded {len(task_ids)} tasks, {args.trials} trials, "
          f"{len(args.conditions)} conditions = {len(jobs)} cells")
    print(f"Provider: {args.provider}/{args.model}, workers: {args.workers}")

    # Pre-flight: API key
    needed_key = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
    if not os.environ.get(needed_key):
        print(f"ERROR: {needed_key} not set"); sys.exit(1)

    # Smoke probe (single completion) to verify provider works
    print("Pre-flight: testing provider with trivial completion...")
    try:
        probe = completion(
            messages=[{"role": "user", "content": "Reply with only: ok"}],
            model=args.model, custom_llm_provider=args.provider, temperature=0.0,
            max_tokens=10,
        )
        probe_text = probe.choices[0].message.content
        print(f"  probe OK: {probe_text!r}")
    except Exception as e:
        print(f"  probe FAILED: {type(e).__name__}: {e}")
        sys.exit(1)

    all_results: List[Dict[str, Any]] = []
    t0 = time.time()
    write_lock = threading.Lock()
    cell_idx = [0]

    def _process(job: Dict[str, Any]) -> Dict[str, Any]:
        return run_one_task(
            job["task_idx"], job["trial"], job["condition"],
            args.provider, args.model, args.user_provider, args.user_model,
            args.env, args.agent_strategy, args.temperature, out_dir,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_to_job = {pool.submit(_process, j): j for j in jobs}
        for fut in as_completed(future_to_job):
            j = future_to_job[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {
                    "task_idx": j["task_idx"], "trial": j["trial"],
                    "condition": j["condition"],
                    "reward": 0.0, "error": f"future {type(e).__name__}: {e}",
                    "elapsed_s": 0, "intervention_fires": 0,
                }
            with write_lock:
                cell_idx[0] += 1
                all_results.append(r)
                ci = cell_idx[0]
                el = time.time() - t0
                eta = el / ci * (len(jobs) - ci) if ci else 0
                rwd = r.get("reward", 0)
                fires = r.get("intervention_fires", 0)
                print(f"[{ci}/{len(jobs)}] task={j['task_idx']} trial={j['trial']} "
                      f"{j['condition']:>12}  reward={rwd:.2f}  intv_fires={fires}  "
                      f"({el:.0f}s elapsed, ETA {eta:.0f}s)", flush=True)
                if ci % 10 == 0:
                    with open(out_dir / "results_partial.json", "w") as f:
                        json.dump({"elapsed_s": el, "n_done": ci, "n_total": len(jobs),
                                   "results": all_results}, f, indent=2, default=str)

    # Compute pass^k per task (for primary metric)
    by_task_cond: Dict[Tuple[int, str], List[float]] = defaultdict(list)
    for r in all_results:
        if r.get("error"):
            continue
        by_task_cond[(r["task_idx"], r["condition"])].append(r["reward"])

    # pass^k = task succeeds on ALL k trials (reward = 1 = full success in tau-bench)
    pass_k_per_task: Dict[Tuple[int, str], Dict[int, int]] = {}
    for (task_idx, cond), rewards in by_task_cond.items():
        rewards_sorted = sorted(rewards, reverse=True)
        pass_k = {}
        for k in range(1, args.trials + 1):
            pass_k[k] = 1 if (len(rewards_sorted) >= k and all(r >= 0.999 for r in rewards_sorted[:k])) else 0
        pass_k_per_task[(task_idx, cond)] = pass_k

    # Aggregate per-condition pass^k counts
    pass_k_summary: Dict[str, Dict[int, int]] = {"control": {}, "intervention": {}}
    for cond in args.conditions:
        for k in range(1, args.trials + 1):
            pass_k_summary[cond][k] = sum(
                pass_k_per_task.get((t, cond), {}).get(k, 0) for t in task_ids
            )

    # McNemar's on pass^trials (primary)
    n_tasks = len(task_ids)
    if "control" in args.conditions and "intervention" in args.conditions:
        primary_k = args.trials
        control_pass = {t for t in task_ids if pass_k_per_task.get((t, "control"), {}).get(primary_k, 0)}
        intv_pass = {t for t in task_ids if pass_k_per_task.get((t, "intervention"), {}).get(primary_k, 0)}
        # b = control pass & intervention fail
        # c = control fail & intervention pass
        b = len(control_pass - intv_pass)
        c = len(intv_pass - control_pass)
        mcnemar = mcnemar_p(b, c)
        delta_pp = (len(intv_pass) - len(control_pass)) / max(n_tasks, 1) * 100
    else:
        b = c = 0
        mcnemar = 1.0
        delta_pp = 0.0

    summary = {
        "model": args.model, "provider": args.provider,
        "user_model": args.user_model, "env": args.env,
        "n_tasks": n_tasks, "trials": args.trials,
        "elapsed_s": time.time() - t0,
        "n_cells": len(all_results),
        "n_errors": sum(1 for r in all_results if r.get("error")),
        "pass_k_summary": pass_k_summary,
        "mcnemar_pass_full_k": {
            "k": args.trials, "b": b, "c": c,
            "p_value": mcnemar, "delta_pp": delta_pp,
        },
        "total_cost_usd": sum(r.get("total_cost", 0) or 0 for r in all_results),
        "total_intervention_fires": sum(r.get("intervention_fires", 0) for r in all_results),
    }

    with open(out_dir / "results.json", "w") as f:
        json.dump({"summary": summary, "results": all_results}, f, indent=2, default=str)

    lines = ["=" * 70,
             f"τ-bench {args.env} | {args.provider}/{args.model} | "
             f"n_tasks={n_tasks} trials={args.trials}",
             "=" * 70,
             f"Elapsed: {summary['elapsed_s']:.0f}s   "
             f"Cells: {summary['n_cells']}   Errors: {summary['n_errors']}",
             f"Total cost: ${summary['total_cost_usd']:.2f}",
             f"Intervention fires: {summary['total_intervention_fires']} "
             f"({summary['total_intervention_fires']/max(summary['n_cells'],1)*100:.1f}% of cells)",
             "",
             "pass^k by condition:"]
    for cond in args.conditions:
        for k in range(1, args.trials + 1):
            cnt = pass_k_summary[cond].get(k, 0)
            lines.append(f"  {cond:>12} pass^{k} = {cnt}/{n_tasks} = {cnt/n_tasks*100:.1f}%")
    if "control" in args.conditions and "intervention" in args.conditions:
        lines.append("")
        lines.append(f"McNemar's exact (pass^{args.trials}):")
        lines.append(f"  b={b} (control pass, intervention fail)")
        lines.append(f"  c={c} (control fail, intervention pass)")
        lines.append(f"  delta = {delta_pp:+.1f}pp   p = {mcnemar:.4f}   "
                     f"{'SIGNIFICANT' if mcnemar < 0.05 else 'not significant'} at alpha=0.05")
    text = "\n".join(lines)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(text + "\n")
    print("\n" + text)


if __name__ == "__main__":
    main()
