"""B1: SWE-bench matched-control extension to n=60 via Opus 4.6 CLI.

Purpose: extend the existing 24-instance matched-control experiment to
60+ instances using Anthropic Claude Opus 4.6 (or 4.7) invoked via the
`claude` CLI. This gives the Fisher's exact test enough power to
confirm the +12.5pp intervention effect at alpha=0.05.

Why CLI (vs SDK): user explicitly approved opus 4.6/4.7 via CLI. The
script invokes `claude --model claude-opus-4-6 --print` as a subprocess
and parses the output. NO Meta CLI guard is enforced -- user confirmed
to ignore that for this run.

Usage:
    cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
    PYTHONPATH=src:. .venv/bin/python3.12 experiments/swebench_n60_opus_cli.py \\
        --n 60 \\
        --model claude-opus-4-6 \\
        --max-iterations 8 \\
        --conditions control intervention \\
        --output-dir results/swebench_n60_opus

    # NOTE: use .venv/bin/python3.12 explicitly. The .venv/bin/python3
    # symlink points at system Python 3.9 on this machine, but the venv
    # site-packages live under python3.12/.

Output:
    results/swebench_n60_opus/results.json
    results/swebench_n60_opus/per_instance/*.json
    results/swebench_n60_opus/summary.txt

Cost estimate: ~$10-20 at $5/$25 per MTok Opus, ~10K input + 1K output
per task * 60 tasks * 2 conditions = ~120 tasks = ~$15.

Runtime: ~6 hours wall-clock (rate-limited by claude CLI throughput).

Statistics: writes Fisher's exact two-sided p-value at end.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from math import comb
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Closed-form Fisher's exact two-sided p-value for 2x2 table."""
    n1, n2, k, N = a + b, c + d, a + c, a + b + c + d

    def hg(x: int) -> float:
        if x < 0 or x > min(n1, k) or (k - x) > n2:
            return 0.0
        return comb(n1, x) * comb(n2, k - x) / comb(N, k)

    p_obs = hg(a)
    p_two = sum(hg(x) for x in range(0, min(n1, k) + 1) if hg(x) <= p_obs + 1e-12)
    return p_two


def load_swebench_instances(n: int = 60, exclude_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Load N SWE-bench Lite instances, excluding any in exclude_ids."""
    from datasets import load_dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    exclude_ids = set(exclude_ids or [])
    instances: List[Dict[str, Any]] = []
    for inst in ds:
        if inst["instance_id"] in exclude_ids:
            continue
        instances.append(dict(inst))
        if len(instances) >= n:
            break
    return instances


def _parse_codex_output(stdout: str) -> str:
    """Strip codex exec's session wrapper from stdout. Same parser as
    experiments/cli_subprocess.py."""
    text = stdout
    if "\ncodex\n" in text:
        text = text.split("\ncodex\n", 1)[1]
    elif text.startswith("codex\n"):
        text = text[len("codex\n"):]
    if "\ntokens used" in text:
        text = text.split("\ntokens used", 1)[0]
    keep = []
    for line in text.splitlines():
        if line.startswith(("hook:", "ERROR codex_core", "2026-", "2027-",
                            "thread ", "shutdown ")):
            continue
        keep.append(line)
    return "\n".join(keep).strip()


def call_opus_cli(prompt: str, model: str, max_tokens: int = 2048,
                  timeout: int = 360) -> Dict[str, Any]:
    """Invoke the appropriate CLI based on model name.

    Dispatch:
      - claude-* models (e.g., claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5)
        go to `claude --model X --print` (stdin = prompt)
      - gpt-* / o*-* / codex-* models go to `codex exec --skip-git-repo-check
        --model X <prompt>` (prompt as argv)

    Function name kept as call_opus_cli for backward compat with run_one_task.

    Returns dict with keys: text, error, latency_s, raw_stdout, raw_stderr.
    """
    start = time.time()
    is_codex = (
        model.startswith("gpt-")
        or model.startswith("o3")
        or model.startswith("o4")
        or model.startswith("codex-")
        or model.startswith("gpt5")
    )
    try:
        if is_codex:
            result = subprocess.run(
                ["codex", "exec", "--skip-git-repo-check", "--model", model, prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="/tmp",
            )
            elapsed = time.time() - start
            if result.returncode != 0:
                return {
                    "text": "",
                    "error": f"codex exit {result.returncode}: {result.stderr[:500]}",
                    "latency_s": elapsed,
                    "raw_stdout": result.stdout,
                    "raw_stderr": result.stderr,
                }
            return {
                "text": _parse_codex_output(result.stdout),
                "error": None,
                "latency_s": elapsed,
                "raw_stdout": result.stdout,
                "raw_stderr": result.stderr,
            }
        else:
            result = subprocess.run(
                ["claude", "--model", model, "--print"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="/tmp",
            )
            elapsed = time.time() - start
            if result.returncode != 0:
                return {
                    "text": "",
                    "error": f"claude exit {result.returncode}: {result.stderr[:500]}",
                    "latency_s": elapsed,
                    "raw_stdout": result.stdout,
                    "raw_stderr": result.stderr,
                }
            return {
                "text": result.stdout.strip(),
                "error": None,
                "latency_s": elapsed,
                "raw_stdout": result.stdout,
                "raw_stderr": result.stderr,
            }
    except subprocess.TimeoutExpired:
        return {
            "text": "",
            "error": f"timeout after {timeout}s",
            "latency_s": time.time() - start,
            "raw_stdout": "",
            "raw_stderr": "",
        }
    except Exception as e:
        return {
            "text": "",
            "error": f"exception: {type(e).__name__}: {e}",
            "latency_s": time.time() - start,
            "raw_stdout": "",
            "raw_stderr": "",
        }


SYSTEM_PROMPT = """You are an autonomous software engineering agent.
You will receive a GitHub issue and repository context.  Your job is to
propose a code patch that fixes the issue.

You have access to these tools (call them by writing JSON):
- search_code(query): search the codebase
- read_file(path, lines): read a file or specific lines
- analyze_error(traceback): analyze an error
- propose_patch(file, diff): propose a unified diff patch
- verify_fix(patch): verify the patch via guardrail check

Reason step-by-step. After at most 8 iterations, propose a final patch.
Output your reasoning in <reasoning>...</reasoning> tags and your final
patch in <patch>...</patch> tags.

If you've already searched for the same query 3+ times without progress,
STOP repeating; try a different file or approach.
"""

INTERVENTION_INSERT = """

[INTERVENTION] You have called search_code with similar queries 3 times
without finding the answer.  Stop searching with the same strategy.
Instead: list 2 alternative approaches and pick the most promising one.
Try a different keyword, file, or function name.
"""


def run_one_task(instance: Dict[str, Any], model: str, max_iterations: int,
                 enable_intervention: bool, instance_dir: Path) -> Dict[str, Any]:
    """Run a single SWE-bench instance via Opus CLI."""
    instance_id = instance["instance_id"]
    problem = instance["problem_statement"]
    repo = instance["repo"]

    history: List[Dict[str, str]] = []
    tool_call_pattern: defaultdict = defaultdict(int)
    iterations = 0
    proposed_patch = False
    answer = ""
    error = None

    base_prompt = SYSTEM_PROMPT + f"\n\nRepository: {repo}\n\nIssue:\n{problem}\n"
    current_prompt = base_prompt

    for it in range(1, max_iterations + 1):
        iterations = it
        # Inject intervention if a search tool was called >=3 times with same args
        if enable_intervention and any(c >= 3 for c in tool_call_pattern.values()):
            current_prompt = current_prompt + INTERVENTION_INSERT

        out = call_opus_cli(current_prompt, model=model, timeout=480)
        history.append({
            "iteration": it,
            "prompt_len": len(current_prompt),
            "response": out["text"][:4000],
            "latency_s": out["latency_s"],
            "error": out["error"],
        })

        if out["error"]:
            error = out["error"]
            break

        text = out["text"]

        # Track repeated search_code calls for intervention trigger
        for m in re.finditer(r'search_code\([^)]*"([^"]+)"', text):
            tool_call_pattern[m.group(1)] += 1

        # Check for final patch
        m = re.search(r'<patch>(.*?)</patch>', text, re.DOTALL)
        if m and m.group(1).strip():
            proposed_patch = True
            answer = m.group(1).strip()
            break

        # Append model output to history for next iteration
        current_prompt = current_prompt + f"\n\n<assistant>{text}</assistant>\n\nContinue."

    result = {
        "instance_id": instance_id,
        "repo": repo,
        "model": model,
        "max_iterations": max_iterations,
        "intervention_enabled": enable_intervention,
        "iterations": iterations,
        "proposed_patch": proposed_patch,
        "answer_len": len(answer),
        "tool_pattern": dict(tool_call_pattern),
        "error": error,
        "history": history,
    }

    # Write per-instance result
    instance_dir.mkdir(parents=True, exist_ok=True)
    cond = "intervention" if enable_intervention else "control"
    with open(instance_dir / f"{instance_id}_{cond}.json", "w") as f:
        # Truncate history responses to keep files small
        for h in result["history"]:
            if len(h["response"]) > 500:
                h["response"] = h["response"][:500] + "...[truncated]"
        json.dump(result, f, indent=2)

    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=60, help="number of instances per condition")
    p.add_argument("--model", default="claude-opus-4-6")
    p.add_argument("--max-iterations", type=int, default=8)
    p.add_argument("--conditions", nargs="+", default=["control", "intervention"])
    p.add_argument("--output-dir", default="results/swebench_n60_opus")
    p.add_argument("--exclude-ids-from", default="results/swebench_matched_control/results.json",
                   help="Skip instance_ids already evaluated in this prior result file")
    args = p.parse_args()

    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    instance_dir = out_dir / "per_instance"

    # Load exclusion list (instances already in matched_control)
    exclude_ids: List[str] = []
    excl_path = PROJECT_ROOT / args.exclude_ids_from
    if excl_path.exists():
        try:
            with open(excl_path) as f:
                prior = json.load(f)
            exclude_ids = [r.get("instance_id") for r in prior.get("results", []) if r.get("instance_id")]
            print(f"Excluding {len(exclude_ids)} prior instances")
        except Exception:
            print(f"Could not parse {excl_path}; running on full dataset")

    instances = load_swebench_instances(n=args.n, exclude_ids=exclude_ids)
    print(f"Loaded {len(instances)} instances")

    # Pre-flight: dispatch to the right CLI based on model name
    is_codex = (
        args.model.startswith("gpt-") or args.model.startswith("o3")
        or args.model.startswith("o4") or args.model.startswith("codex-")
        or args.model.startswith("gpt5")
    )
    cli_name = "codex" if is_codex else "claude"
    cli_check = subprocess.run(["which", cli_name], capture_output=True, text=True)
    if cli_check.returncode != 0:
        print(f"ERROR: `{cli_name}` CLI not found in PATH")
        sys.exit(1)
    print(f"{cli_name} CLI: {cli_check.stdout.strip()}")

    # One-shot smoke probe: a trivial 2-token call. If this hangs >120s
    # the user has not yet cleared the interactive ack gate; print a
    # clear remediation message and exit.
    print(f"Probing {cli_name} CLI with trivial call (up to 120s)...", flush=True)
    probe = call_opus_cli("Reply with only the word: ok", model=args.model, timeout=120)
    if probe["error"]:
        print(f"\nERROR: {cli_name} CLI probe failed: {probe['error']}")
        print(f"Latency: {probe['latency_s']:.1f}s")
        if "timeout" in probe["error"].lower():
            print(f"\nMost likely cause: the Meta `{cli_name}` CLI requires a one-time")
            print("interactive ack on this machine. Run this manually first:")
            if is_codex:
                print(f"\n    codex exec --skip-git-repo-check --model {args.model} 'say only: pong'")
            else:
                print(f"\n    echo 'say only: pong' | claude --model {args.model} --print")
            print("\nWhen prompted, type EXACTLY:  I HAVE REVIEWED AND VERIFIED")
            print("Then re-run this script.")
        sys.exit(1)
    print(f"  probe OK in {probe['latency_s']:.1f}s; response: {probe['text'][:80]!r}")

    all_results: List[Dict[str, Any]] = []

    t0 = time.time()
    for cond in args.conditions:
        enable_intv = (cond == "intervention")
        print(f"\n=== Condition: {cond} (intervention={enable_intv}) ===")
        for i, inst in enumerate(instances, 1):
            print(f"[{cond} {i}/{len(instances)}] {inst['instance_id']}", flush=True)
            try:
                r = run_one_task(inst, args.model, args.max_iterations,
                                 enable_intv, instance_dir)
            except Exception as e:
                print(f"  EXCEPTION: {type(e).__name__}: {e}")
                r = {
                    "instance_id": inst["instance_id"],
                    "repo": inst.get("repo"),
                    "intervention_enabled": enable_intv,
                    "iterations": 0,
                    "proposed_patch": False,
                    "answer_len": 0,
                    "tool_pattern": {},
                    "error": str(e),
                    "history": [],
                }
            all_results.append(r)

            # Periodic save
            if i % 5 == 0:
                with open(out_dir / "results_partial.json", "w") as f:
                    json.dump({"elapsed_s": time.time() - t0,
                               "n_done": len(all_results),
                               "results": all_results}, f, indent=2)

    # Summary statistics
    by_cond: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in all_results:
        cond = "intervention" if r["intervention_enabled"] else "control"
        by_cond[cond].append(r)

    summary: Dict[str, Any] = {
        "model": args.model,
        "n_per_condition": args.n,
        "max_iterations": args.max_iterations,
        "elapsed_s": time.time() - t0,
        "by_condition": {},
    }
    for cond, runs in by_cond.items():
        n = len(runs)
        success = sum(1 for r in runs if r["proposed_patch"])
        summary["by_condition"][cond] = {
            "n": n,
            "success": success,
            "rate": success / n if n else 0.0,
        }

    if "control" in by_cond and "intervention" in by_cond:
        a = summary["by_condition"]["intervention"]["success"]
        b = summary["by_condition"]["intervention"]["n"] - a
        c = summary["by_condition"]["control"]["success"]
        d = summary["by_condition"]["control"]["n"] - c
        p_two = fisher_exact_two_sided(a, b, c, d)
        summary["fisher_exact"] = {
            "intervention_table": [a, b],
            "control_table": [c, d],
            "p_two_sided": p_two,
            "significant_005": p_two < 0.05,
        }

    with open(out_dir / "results.json", "w") as f:
        json.dump({"summary": summary, "results": all_results}, f, indent=2)

    # Human-readable summary
    lines = [
        "=" * 60,
        f"B1: SWE-bench n={args.n} matched control via {args.model} CLI",
        "=" * 60,
        f"Elapsed: {summary['elapsed_s']:.0f}s",
        "",
    ]
    for cond, stats in summary["by_condition"].items():
        lines.append(f"  {cond:15s} {stats['success']}/{stats['n']} = {stats['rate']*100:.1f}%")
    if "fisher_exact" in summary:
        fe = summary["fisher_exact"]
        lines.append("")
        lines.append(f"Fisher's exact two-sided p = {fe['p_two_sided']:.4f}")
        lines.append(f"Significant at alpha=0.05:  {fe['significant_005']}")
    summary_text = "\n".join(lines)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(summary_text + "\n")
    print("\n" + summary_text)


if __name__ == "__main__":
    main()
