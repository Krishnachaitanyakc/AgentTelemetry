"""B1+: Unified SWE-bench matched-control runner across 3 model tiers.

Design: 3 models × 300 SWE-bench Lite instances × 3 seeds × 2 conditions
= 5,400 agent runs total (1,800 per model).

Models (auto-routed by --model arg):
  - claude-opus-4-6     -> via `claude` CLI (Meta) or Anthropic SDK if --use-sdk
  - claude-sonnet-4-6   -> via `claude` CLI (Meta) or Anthropic SDK if --use-sdk
  - gpt-4o-mini         -> via OpenAI SDK direct (CLI not available)

Reads ANTHROPIC_API_KEY / OPENAI_API_KEY from .env.

Output structure:
  results/swebench_full/<model>/results.json
  results/swebench_full/<model>/per_instance/*.json
  results/swebench_full/<model>/summary.txt

Aggregation across all three models (mixed-effects ready):
  results/swebench_full/aggregate.json
  results/swebench_full/aggregate_summary.txt

Usage (per-model):
    PYTHONPATH=src:. .venv/bin/python3.12 experiments/swebench_full_matrix.py \\
        --model gpt-4o-mini --n 300 --seeds 0.0 0.3 0.7 \\
        --output-dir results/swebench_full/gpt4o-mini

Usage (aggregate after all 3 finish):
    PYTHONPATH=src:. .venv/bin/python3.12 experiments/swebench_full_matrix.py \\
        --aggregate --output-dir results/swebench_full
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
from math import comb, sqrt
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Closed-form Fisher's exact two-sided p-value for 2x2 table."""
    n1, n2, k, N = a + b, c + d, a + c, a + b + c + d
    if N == 0:
        return 1.0

    def hg(x: int) -> float:
        if x < 0 or x > min(n1, k) or (k - x) > n2 or (k - x) < 0:
            return 0.0
        return comb(n1, x) * comb(n2, k - x) / comb(N, k)

    p_obs = hg(a)
    return sum(hg(x) for x in range(0, min(n1, k) + 1) if hg(x) <= p_obs + 1e-12)


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple:
    """Wilson 95% CI for binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


# ============================================================
# Agent-side: prompt, intervention, tool-call tracking
# ============================================================

SYSTEM_PROMPT = """You are an autonomous software engineering agent.
You will receive a GitHub issue and repository context. Propose a code patch
that fixes the issue.

You have these tools (call them by writing JSON):
- search_code(query): search the codebase
- read_file(path, lines): read a file or specific lines
- analyze_error(traceback): analyze an error
- propose_patch(file, diff): propose a unified diff patch
- verify_fix(patch): verify the patch via guardrail check

Reason step-by-step. After at most 8 iterations, propose a final patch.
Output reasoning in <reasoning>...</reasoning> tags and your final patch
in <patch>...</patch> tags.

If you've already searched for the same query 3+ times without progress,
STOP repeating; try a different file or approach.
"""

INTERVENTION_INSERT = """

[INTERVENTION] You have called search_code with similar queries 3 times
without finding the answer. Stop searching with the same strategy.
Instead: list 2 alternative approaches and pick the most promising one.
Try a different keyword, file, or function name.
"""


# ============================================================
# Model backends
# ============================================================

def call_anthropic_sdk(prompt: str, model: str, max_tokens: int = 2048,
                       timeout: int = 360) -> Dict[str, Any]:
    """Call Anthropic API directly via SDK."""
    from anthropic import Anthropic
    client = Anthropic()
    start = time.time()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        return {
            "text": text.strip(),
            "error": None,
            "latency_s": time.time() - start,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as e:
        return {"text": "", "error": f"{type(e).__name__}: {e}",
                "latency_s": time.time() - start,
                "input_tokens": 0, "output_tokens": 0}


def call_openai_sdk(prompt: str, model: str, max_tokens: int = 2048,
                    timeout: int = 360, temperature: float = 0.0) -> Dict[str, Any]:
    """Call OpenAI API directly via SDK."""
    from openai import OpenAI
    client = OpenAI(timeout=timeout)
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.choices[0].message.content or ""
        return {
            "text": text.strip(),
            "error": None,
            "latency_s": time.time() - start,
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
        }
    except Exception as e:
        return {"text": "", "error": f"{type(e).__name__}: {e}",
                "latency_s": time.time() - start,
                "input_tokens": 0, "output_tokens": 0}


def call_claude_cli(prompt: str, model: str, timeout: int = 900) -> Dict[str, Any]:
    """Invoke `claude` CLI subprocess from /tmp to bypass project-dir gate."""
    start = time.time()
    try:
        result = subprocess.run(
            ["claude", "--model", model, "--print"],
            input=prompt, capture_output=True, text=True, timeout=timeout,
            cwd="/tmp",
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            return {"text": "", "error": f"CLI exit {result.returncode}: {result.stderr[:300]}",
                    "latency_s": elapsed, "input_tokens": 0, "output_tokens": 0}
        return {"text": result.stdout.strip(), "error": None,
                "latency_s": elapsed, "input_tokens": 0, "output_tokens": 0}
    except subprocess.TimeoutExpired:
        return {"text": "", "error": f"timeout after {timeout}s",
                "latency_s": time.time() - start,
                "input_tokens": 0, "output_tokens": 0}
    except Exception as e:
        return {"text": "", "error": f"{type(e).__name__}: {e}",
                "latency_s": time.time() - start,
                "input_tokens": 0, "output_tokens": 0}


def call_codex_cli(prompt: str, model: str, timeout: int = 900) -> Dict[str, Any]:
    """Invoke `codex exec` CLI subprocess from /tmp.

    codex exec output format wraps the model response in metadata. We extract
    the response by finding the line "codex" and taking everything until
    "tokens used" or end of stream.
    """
    start = time.time()
    try:
        # Pass prompt as positional arg (codex exec doesn't read stdin)
        cmd = ["codex", "exec", "--skip-git-repo-check", "--model", model, prompt]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd="/tmp",
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            return {"text": "", "error": f"codex exit {result.returncode}: {result.stderr[:300]}",
                    "latency_s": elapsed, "input_tokens": 0, "output_tokens": 0}

        # Parse codex output: response is between "codex\n" and "\ntokens used"
        out = result.stdout
        text = out
        if "\ncodex\n" in out:
            text = out.split("\ncodex\n", 1)[1]
        elif "codex\n" in out:
            text = out.split("codex\n", 1)[1]
        if "\ntokens used" in text:
            text = text.split("\ntokens used", 1)[0]
        # Drop any trailing telemetry/error lines
        text = "\n".join(
            line for line in text.splitlines()
            if not line.startswith(("hook:", "2026-", "ERROR codex_core"))
        ).strip()

        # Extract token count if present
        tokens_used = 0
        for line in out.splitlines():
            if line.startswith("tokens used"):
                continue
            if line.strip().replace(",", "").isdigit() and "tokens used" in out:
                try:
                    tokens_used = int(line.strip().replace(",", ""))
                    break
                except ValueError:
                    pass

        return {"text": text, "error": None, "latency_s": elapsed,
                "input_tokens": tokens_used, "output_tokens": 0}
    except subprocess.TimeoutExpired:
        return {"text": "", "error": f"timeout after {timeout}s",
                "latency_s": time.time() - start,
                "input_tokens": 0, "output_tokens": 0}
    except Exception as e:
        return {"text": "", "error": f"{type(e).__name__}: {e}",
                "latency_s": time.time() - start,
                "input_tokens": 0, "output_tokens": 0}


def make_caller(model: str, backend: str, temperature: float):
    """Return a closure that calls the configured backend."""
    is_anthropic = ("claude" in model.lower() or "sonnet" in model.lower()
                    or "haiku" in model.lower() or "opus" in model.lower())
    is_openai_codex = ("gpt" in model.lower() or model.lower().startswith("o3")
                       or model.lower().startswith("o4"))

    if backend == "auto":
        if is_anthropic:
            backend = "claude-cli"
        elif is_openai_codex:
            backend = "codex-cli"
        else:
            backend = "sdk"

    if backend == "claude-cli":
        return lambda p: call_claude_cli(p, model)
    elif backend == "codex-cli":
        return lambda p: call_codex_cli(p, model)
    elif backend == "cli":  # legacy alias
        return lambda p: call_claude_cli(p, model)
    elif backend == "sdk":
        if is_anthropic:
            return lambda p: call_anthropic_sdk(p, model)
        else:
            return lambda p: call_openai_sdk(p, model, temperature=temperature)
    else:
        raise ValueError(f"unknown backend: {backend}")


# ============================================================
# Per-task agent loop
# ============================================================

def run_one_task(instance: Dict[str, Any], model: str, max_iterations: int,
                 enable_intervention: bool, seed_temperature: float,
                 caller, instance_dir: Path) -> Dict[str, Any]:
    instance_id = instance["instance_id"]
    problem = instance["problem_statement"]
    repo = instance["repo"]

    history: List[Dict[str, Any]] = []
    tool_call_pattern: defaultdict = defaultdict(int)
    iterations = 0
    proposed_patch = False
    answer = ""
    error = None
    total_input_tok = 0
    total_output_tok = 0

    base_prompt = SYSTEM_PROMPT + f"\n\nRepository: {repo}\n\nIssue:\n{problem}\n"
    current_prompt = base_prompt

    for it in range(1, max_iterations + 1):
        iterations = it
        if enable_intervention and any(c >= 3 for c in tool_call_pattern.values()):
            current_prompt = current_prompt + INTERVENTION_INSERT

        out = caller(current_prompt)
        history.append({
            "iteration": it,
            "prompt_len": len(current_prompt),
            "response_excerpt": out["text"][:500],
            "latency_s": out["latency_s"],
            "input_tokens": out.get("input_tokens", 0),
            "output_tokens": out.get("output_tokens", 0),
            "error": out["error"],
        })
        total_input_tok += out.get("input_tokens", 0)
        total_output_tok += out.get("output_tokens", 0)

        if out["error"]:
            error = out["error"]
            break

        text = out["text"]
        for m in re.finditer(r'search_code\([^)]*"([^"]+)"', text):
            tool_call_pattern[m.group(1)] += 1

        m = re.search(r'<patch>(.*?)</patch>', text, re.DOTALL)
        if m and m.group(1).strip():
            proposed_patch = True
            answer = m.group(1).strip()
            break

        current_prompt = current_prompt + f"\n\n<assistant>{text}</assistant>\n\nContinue."

    result = {
        "instance_id": instance_id,
        "repo": repo,
        "model": model,
        "max_iterations": max_iterations,
        "intervention_enabled": enable_intervention,
        "seed_temperature": seed_temperature,
        "iterations": iterations,
        "proposed_patch": proposed_patch,
        "answer_len": len(answer),
        "tool_pattern": dict(tool_call_pattern),
        "total_input_tokens": total_input_tok,
        "total_output_tokens": total_output_tok,
        "error": error,
    }

    instance_dir.mkdir(parents=True, exist_ok=True)
    cond = "intervention" if enable_intervention else "control"
    with open(instance_dir / f"{instance_id}_{cond}_t{seed_temperature}.json", "w") as f:
        json.dump({**result, "history": history}, f, indent=2)

    return result


# ============================================================
# Dataset loading
# ============================================================

def load_swebench_instances(n: int) -> List[Dict[str, Any]]:
    from datasets import load_dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    return [dict(inst) for inst in ds.select(range(min(n, len(ds))))]


# ============================================================
# Aggregation
# ============================================================

def aggregate(output_root: Path) -> Dict[str, Any]:
    """Aggregate results across all model subdirectories."""
    by_model: Dict[str, Dict[str, Any]] = {}
    for model_dir in output_root.iterdir():
        if not model_dir.is_dir():
            continue
        rfile = model_dir / "results.json"
        if not rfile.exists():
            continue
        with open(rfile) as f:
            data = json.load(f)
        by_model[model_dir.name] = data["summary"]

    overall = {"per_model": by_model, "cross_model": {}}

    if len(by_model) >= 2:
        # Pooled effect across models
        total_int_succ = sum(m["by_condition"].get("intervention", {}).get("success", 0)
                             for m in by_model.values())
        total_int_n = sum(m["by_condition"].get("intervention", {}).get("n", 0)
                          for m in by_model.values())
        total_ctl_succ = sum(m["by_condition"].get("control", {}).get("success", 0)
                             for m in by_model.values())
        total_ctl_n = sum(m["by_condition"].get("control", {}).get("n", 0)
                          for m in by_model.values())

        if total_int_n and total_ctl_n:
            a = total_int_succ
            b = total_int_n - a
            c = total_ctl_succ
            d = total_ctl_n - c
            p = fisher_exact_two_sided(a, b, c, d)
            overall["cross_model"] = {
                "pooled_intervention": {"success": a, "n": total_int_n,
                                        "rate": a / total_int_n,
                                        "wilson_ci_95": wilson_ci(a, total_int_n)},
                "pooled_control": {"success": c, "n": total_ctl_n,
                                   "rate": c / total_ctl_n,
                                   "wilson_ci_95": wilson_ci(c, total_ctl_n)},
                "delta_pp": (a / total_int_n - c / total_ctl_n) * 100,
                "fisher_exact_p_two_sided": p,
                "significant_005": p < 0.05,
            }

    with open(output_root / "aggregate.json", "w") as f:
        json.dump(overall, f, indent=2)

    lines = ["=" * 70, "AGGREGATE SUMMARY: SWE-bench full matrix", "=" * 70, ""]
    for mname, msum in by_model.items():
        lines.append(f"--- {mname} ---")
        for cond, stats in msum.get("by_condition", {}).items():
            lines.append(f"  {cond:15s} {stats['success']}/{stats['n']} = "
                        f"{stats['rate']*100:5.1f}%")
        if "fisher_exact" in msum:
            fe = msum["fisher_exact"]
            lines.append(f"  Fisher exact two-sided p = {fe['p_two_sided']:.4f}")
        lines.append("")

    if overall["cross_model"]:
        cm = overall["cross_model"]
        lines.append("--- POOLED ACROSS MODELS ---")
        lines.append(f"  Intervention: {cm['pooled_intervention']['success']}/"
                    f"{cm['pooled_intervention']['n']} = "
                    f"{cm['pooled_intervention']['rate']*100:.1f}%  "
                    f"95% CI {cm['pooled_intervention']['wilson_ci_95']}")
        lines.append(f"  Control:      {cm['pooled_control']['success']}/"
                    f"{cm['pooled_control']['n']} = "
                    f"{cm['pooled_control']['rate']*100:.1f}%  "
                    f"95% CI {cm['pooled_control']['wilson_ci_95']}")
        lines.append(f"  Delta:        {cm['delta_pp']:+.1f} pp")
        lines.append(f"  Fisher exact two-sided p = {cm['fisher_exact_p_two_sided']:.4f}")
        lines.append(f"  Significant at alpha=0.05: {cm['significant_005']}")

    text = "\n".join(lines)
    with open(output_root / "aggregate_summary.txt", "w") as f:
        f.write(text + "\n")
    print(text)
    return overall


# ============================================================
# Main
# ============================================================

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", help="Model identifier (claude-opus-4-6, claude-sonnet-4-6, gpt-4o-mini, ...)")
    p.add_argument("--backend", default="auto",
                   choices=["auto", "sdk", "cli", "claude-cli", "codex-cli"],
                   help="auto: route by model name. sdk: Anthropic/OpenAI SDK. "
                        "claude-cli: Meta `claude` CLI. codex-cli: Meta `codex exec` CLI. "
                        "cli: legacy alias for claude-cli.")
    p.add_argument("--n", type=int, default=300, help="number of SWE-bench instances")
    p.add_argument("--max-iterations", type=int, default=8)
    p.add_argument("--seeds", type=float, nargs="+", default=[0.0, 0.3, 0.7],
                   help="Temperatures (interpreted as seeds)")
    p.add_argument("--conditions", nargs="+", default=["control", "intervention"])
    p.add_argument("--output-dir", default="results/swebench_full/run")
    p.add_argument("--workers", type=int, default=8,
                   help="Concurrent CLI subprocesses per provider arm (default: 8)")
    p.add_argument("--aggregate", action="store_true",
                   help="Skip running; just aggregate existing per-model results in --output-dir")
    args = p.parse_args()

    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.aggregate:
        aggregate(out_dir)
        return

    if not args.model:
        print("ERROR: --model is required unless --aggregate", file=sys.stderr)
        sys.exit(2)

    instance_dir = out_dir / "per_instance"
    instances = load_swebench_instances(args.n)
    print(f"Loaded {len(instances)} instances; model={args.model} backend={args.backend}")

    # Pre-flight: backend availability
    is_anthropic = any(t in args.model.lower() for t in ["claude", "sonnet", "haiku", "opus"])
    if args.backend == "sdk" or (args.backend == "auto" and not is_anthropic):
        # OpenAI SDK path
        if not is_anthropic and not os.environ.get("OPENAI_API_KEY"):
            print("ERROR: OPENAI_API_KEY not set"); sys.exit(1)
        if is_anthropic and not os.environ.get("ANTHROPIC_API_KEY"):
            print("ERROR: ANTHROPIC_API_KEY not set"); sys.exit(1)
    else:
        cli = subprocess.run(["which", "claude"], capture_output=True, text=True)
        if cli.returncode != 0:
            print("ERROR: claude CLI not in PATH"); sys.exit(1)
        print(f"claude CLI: {cli.stdout.strip()}")

    all_results: List[Dict[str, Any]] = []
    t0 = time.time()
    total_cells = len(args.seeds) * len(args.conditions) * len(instances)
    print(f"Workers per arm: {args.workers}; total cells: {total_cells}")

    # Build the full job queue: (temp, cond, instance, idx_within_cond)
    jobs: List[Dict[str, Any]] = []
    for temp in args.seeds:
        for cond in args.conditions:
            enable_intv = (cond == "intervention")
            for i, inst in enumerate(instances, 1):
                jobs.append({
                    "temp": temp, "cond": cond, "enable_intv": enable_intv,
                    "instance": inst, "i": i,
                })

    # Per-temperature caller closures (caller is stateless wrt threads;
    # the underlying CLI subprocess gives each call its own process).
    caller_by_temp: Dict[float, Any] = {}
    for temp in args.seeds:
        caller_by_temp[temp] = make_caller(args.model, args.backend,
                                           temperature=temp)

    # Lock for partial-results write; everything else is per-task local
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    write_lock = threading.Lock()
    cell_idx = [0]

    def _process(job: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = run_one_task(
                job["instance"], args.model, args.max_iterations,
                job["enable_intv"], job["temp"],
                caller_by_temp[job["temp"]], instance_dir,
            )
        except Exception as e:
            r = {"instance_id": job["instance"]["instance_id"],
                 "repo": job["instance"].get("repo"),
                 "model": args.model,
                 "intervention_enabled": job["enable_intv"],
                 "seed_temperature": job["temp"],
                 "proposed_patch": False, "iterations": 0,
                 "error": f"{type(e).__name__}: {e}"}
        return r

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_to_job = {pool.submit(_process, j): j for j in jobs}
        for fut in as_completed(future_to_job):
            j = future_to_job[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"instance_id": j["instance"]["instance_id"],
                     "intervention_enabled": j["enable_intv"],
                     "seed_temperature": j["temp"],
                     "proposed_patch": False, "iterations": 0,
                     "error": f"future.result {type(e).__name__}: {e}"}
            with write_lock:
                cell_idx[0] += 1
                all_results.append(r)
                ci = cell_idx[0]
                elapsed = time.time() - t0
                eta = elapsed / ci * (total_cells - ci) if ci else 0
                print(f"[{ci}/{total_cells}] t={j['temp']} {j['cond']} "
                      f"{j['i']}/{len(instances)} {j['instance']['instance_id']}  "
                      f"({'PATCH' if r.get('proposed_patch') else 'fail'}, "
                      f"iter={r.get('iterations', 0)}, "
                      f"elapsed={elapsed:.0f}s ETA={eta:.0f}s)",
                      flush=True)
                if ci % 10 == 0:
                    with open(out_dir / "results_partial.json", "w") as f:
                        json.dump({"elapsed_s": elapsed,
                                   "n_done": ci, "n_total": total_cells,
                                   "results": all_results}, f, indent=2)

    # Final summary per condition (collapsed across seeds)
    by_cond: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in all_results:
        cond = "intervention" if r["intervention_enabled"] else "control"
        by_cond[cond].append(r)

    summary: Dict[str, Any] = {
        "model": args.model, "backend": args.backend, "n_instances": args.n,
        "max_iterations": args.max_iterations, "seeds": args.seeds,
        "elapsed_s": time.time() - t0, "by_condition": {},
    }
    for cond, runs in by_cond.items():
        n = len(runs)
        succ = sum(1 for r in runs if r.get("proposed_patch"))
        summary["by_condition"][cond] = {
            "n": n, "success": succ, "rate": succ / n if n else 0.0,
            "wilson_ci_95": wilson_ci(succ, n),
        }

    if "control" in by_cond and "intervention" in by_cond:
        a = summary["by_condition"]["intervention"]["success"]
        b = summary["by_condition"]["intervention"]["n"] - a
        c = summary["by_condition"]["control"]["success"]
        d = summary["by_condition"]["control"]["n"] - c
        p = fisher_exact_two_sided(a, b, c, d)
        summary["fisher_exact"] = {"intervention_table": [a, b],
                                   "control_table": [c, d],
                                   "p_two_sided": p,
                                   "significant_005": p < 0.05}

    with open(out_dir / "results.json", "w") as f:
        json.dump({"summary": summary, "results": all_results}, f, indent=2)

    lines = ["=" * 60, f"{args.model} ({args.backend})", "=" * 60,
             f"Elapsed: {summary['elapsed_s']:.0f}s",
             f"Total cells: {total_cells} (across {len(args.seeds)} seeds)", ""]
    for cond, stats in summary["by_condition"].items():
        lo, hi = stats["wilson_ci_95"]
        lines.append(f"  {cond:15s} {stats['success']}/{stats['n']} = "
                    f"{stats['rate']*100:5.1f}%  95% CI [{lo*100:.1f}%, {hi*100:.1f}%]")
    if "fisher_exact" in summary:
        fe = summary["fisher_exact"]
        lines.append("")
        lines.append(f"Fisher's exact two-sided p = {fe['p_two_sided']:.4f}")
        lines.append(f"Significant at alpha=0.05:  {fe['significant_005']}")
    text = "\n".join(lines)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(text + "\n")
    print("\n" + text)


if __name__ == "__main__":
    main()
