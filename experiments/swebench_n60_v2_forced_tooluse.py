"""B1v2: SWE-bench n=60 matched-control with FORCED tool-use harness.

Background: experiments/swebench_n60_opus_cli.py (the original harness)
discovered that modern models (Opus 4.6, Sonnet 4.6, Haiku 4.5, GPT-5.5)
short-circuit the ReAct loop and emit a `<patch>` on iteration 1 without
ever calling `search_code`. This makes the original AIware-style
intervention untestable: the trigger condition (>=3 identical search
calls) never fires.

This v2 harness fixes the bug by:
  1. SYSTEM PROMPT forces tool use: model MUST call search_code at least
     `min_searches` times before emitting a `<patch>` block.
  2. PATCH SUPPRESSION: if iteration < min_searches and the response
     contains a <patch> block, we strip it and append a "you must search
     first" reminder.
  3. ROBUST TOOL-CALL PARSING: matches both legacy
     `search_code("query")` and JSON `<tool_call>{"name":...}</tool_call>`
     formats.
  4. SIMULATED TOOL RESPONSES: returns a deterministic short snippet so
     the model has something to react to and can converge or loop.
  5. INTERVENTION TRIGGERS more aggressively: any single search query
     repeated >= min_repeats times triggers the strategy-change prompt.

This re-creates the conditions under which the original AIware n=24
finding was generated, allowing a fair test of the +12.5pp claim.

Usage (same as original):
    cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
    PYTHONPATH=src:. .venv/bin/python3.12 experiments/swebench_n60_v2_forced_tooluse.py \\
        --n 60 --model claude-haiku-4-5 --max-iterations 8 \\
        --min-searches 3 --min-repeats 3 \\
        --conditions control intervention \\
        --output-dir results/swebench_n60_v2_haiku
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
    n1, n2, k, N = a + b, c + d, a + c, a + b + c + d
    def hg(x: int) -> float:
        if x < 0 or x > min(n1, k) or (k - x) > n2:
            return 0.0
        return comb(n1, x) * comb(n2, k - x) / comb(N, k)
    p_obs = hg(a)
    return sum(hg(x) for x in range(0, min(n1, k) + 1) if hg(x) <= p_obs + 1e-12)


def load_swebench_instances(n: int = 60, exclude_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
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


def _parse_gemini_output(stdout: str) -> str:
    """Strip gemini CLI's massive noise (warnings, errors, stack traces) and
    keep only the substantive response. The gemini CLI prints:
      - Header: 'Gemini CLI at Meta...'
      - [WARN] [MemoryDiscovery] ... lines
      - 'innerError Error: ...' Node module-not-found stack trace
      - 'Loading extension: Meta', 'Error during discovery for MCP server'
      - The actual response (one or more lines)
      - Trailing JSON stack-trace blobs from OpenTelemetry export errors
    We keep lines that are not in any of the noise categories."""
    keep = []
    for line in stdout.splitlines():
        s = line.strip()
        if not s:
            continue
        # Skip header / warnings / known noise
        if s.startswith("Gemini CLI at Meta"):
            continue
        if s.startswith("[WARN]"):
            continue
        if s.startswith("[ERROR]"):
            continue
        if s.startswith("Loading extension"):
            continue
        if s.startswith("Error during discovery"):
            continue
        if s.startswith("innerError"):
            continue
        if s.startswith("Require stack:"):
            continue
        if s.startswith("- /usr/local/bin/gemini_cli"):
            continue
        if s.startswith("at ") and ("(" in s or "node:" in s):
            continue
        if s.startswith("at Object.") or s.startswith("at TracingChannel") or s.startswith("at Module"):
            continue
        if s.startswith("at process") or s.startswith("at AsyncLocal") or s.startswith("at "):
            continue
        if s.startswith("Timeout of "):
            continue
        if s.startswith("The 'metricReader' option is deprecated"):
            continue
        if s.startswith("code: '") or s.startswith("requireStack:"):
            continue
        if s.startswith("'") or s == "}" or s == "]" or s == "{":
            continue
        # Trailing JSON OTel error blobs — start with `{"stack":`
        if s.startswith('{"stack":') or s.startswith('{"message":') or s.startswith('{"name":'):
            continue
        # Skip MCP / general infra messages
        if "MCP server" in s and "Connection closed" in s:
            continue
        keep.append(s)
    return "\n".join(keep).strip()


def call_cli(prompt: str, model: str, timeout: int = 360) -> Dict[str, Any]:
    """Dispatch to the right CLI based on model name."""
    start = time.time()
    is_codex = (
        model.startswith("gpt-") or model.startswith("o3")
        or model.startswith("o4") or model.startswith("codex-")
        or model.startswith("gpt5")
    )
    is_gemini = model.startswith("gemini")
    try:
        if is_codex:
            r = subprocess.run(
                ["codex", "exec", "--skip-git-repo-check", "--model", model, prompt],
                capture_output=True, text=True, timeout=timeout, cwd="/tmp",
            )
            elapsed = time.time() - start
            if r.returncode != 0:
                return {"text": "", "error": f"codex exit {r.returncode}: {r.stderr[:300]}",
                        "latency_s": elapsed}
            return {"text": _parse_codex_output(r.stdout), "error": None,
                    "latency_s": elapsed}
        elif is_gemini:
            r = subprocess.run(
                ["gemini", "-m", model, "-p", prompt],
                capture_output=True, text=True, timeout=timeout, cwd="/tmp",
            )
            elapsed = time.time() - start
            if r.returncode != 0:
                return {"text": "", "error": f"gemini exit {r.returncode}: {r.stderr[:300]}",
                        "latency_s": elapsed}
            return {"text": _parse_gemini_output(r.stdout), "error": None,
                    "latency_s": elapsed}
        else:
            r = subprocess.run(
                ["claude", "--model", model, "--print"],
                input=prompt, capture_output=True, text=True,
                timeout=timeout, cwd="/tmp",
            )
            elapsed = time.time() - start
            if r.returncode != 0:
                return {"text": "", "error": f"claude exit {r.returncode}: {r.stderr[:300]}",
                        "latency_s": elapsed}
            return {"text": r.stdout.strip(), "error": None, "latency_s": elapsed}
    except subprocess.TimeoutExpired:
        return {"text": "", "error": f"timeout after {timeout}s",
                "latency_s": time.time() - start}
    except Exception as e:
        return {"text": "", "error": f"{type(e).__name__}: {e}",
                "latency_s": time.time() - start}


# ---- Robust tool-call extraction ----
# Supports two formats the modern CLIs emit:
#   1. Legacy AIware style: search_code("query")  or  search_code('query')
#   2. JSON style:          <tool_call>{"name":"search_code","arguments":{"query":"..."}}</tool_call>

LEGACY_TOOLCALL_RE = re.compile(
    r'search_code\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    re.IGNORECASE,
)
JSON_TOOLCALL_RE = re.compile(
    r'<tool_call>\s*(\{[^<]*?\})\s*</tool_call>',
    re.DOTALL,
)
# Markdown-fenced search call: ```tool_call\n{"name":"search_code","arguments":{"query":"..."}}\n```
MD_TOOLCALL_RE = re.compile(
    r'```(?:tool_call|json)\s*\n(\{[^`]*?"search_code"[^`]*?\})\s*\n```',
    re.DOTALL | re.IGNORECASE,
)
# Bare instruction-following: I will search for "X" / Let me search the codebase for "X"
NL_SEARCH_RE = re.compile(
    r'(?:search\s+(?:for|the\s+codebase\s+for|code\s+for)|searching\s+for)\s+[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)


def extract_search_queries(text: str) -> List[str]:
    """Extract every search_code(query) call from text in any supported format."""
    queries: List[str] = []
    for m in LEGACY_TOOLCALL_RE.finditer(text):
        queries.append(m.group(1).strip())
    for m in JSON_TOOLCALL_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
            if obj.get("name") == "search_code":
                args = obj.get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                q = args.get("query") or args.get("q") or ""
                if q:
                    queries.append(str(q).strip())
        except (json.JSONDecodeError, AttributeError):
            continue
    for m in MD_TOOLCALL_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
            if obj.get("name") == "search_code":
                args = obj.get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                q = args.get("query") or args.get("q") or ""
                if q:
                    queries.append(str(q).strip())
        except (json.JSONDecodeError, AttributeError):
            continue
    for m in NL_SEARCH_RE.finditer(text):
        queries.append(m.group(1).strip())
    return queries


PATCH_RE = re.compile(r'<patch>(.*?)</patch>', re.DOTALL)
# Markdown code block patches: ```diff ... ``` or ```python ... ``` etc.
# Many models (especially Gemini, sometimes GPT) emit patches in fenced blocks.
MD_DIFF_RE = re.compile(r'```(?:diff|patch)\s*\n(.*?)\n```', re.DOTALL | re.IGNORECASE)
MD_CODE_RE = re.compile(r'```(?:python|py|java|javascript|js|cpp|c|go|rust)\s*\n(.*?)\n```', re.DOTALL | re.IGNORECASE)
# Unified diff body without fences: `--- a/path` ... `+++ b/path` ... `@@ ... @@`
RAW_DIFF_RE = re.compile(r'(--- a/.+?\n\+\+\+ b/.+?\n@@.+?)(?=\n(?:```|---\s+a/|<patch>|<reasoning>|$))', re.DOTALL)


def extract_patch(text: str) -> Optional[str]:
    """Extract a proposed patch from the model's response.

    Accepts (in priority order):
      1. <patch>...</patch>                — the protocol-specified format
      2. ```diff ... ``` or ```patch ...```— Gemini frequently uses this
      3. Raw unified diff (--- a/, +++ b/, @@) — sometimes emitted bare
      4. ```python ... ``` containing a substantive code body — last-resort
         heuristic; many models propose 'code that fixes the issue' in
         a fenced block without an explicit diff. This is a permissive
         capture that records the intent to commit a patch even when
         format compliance is poor.

    Returns None if no patch-like content is found, else the captured body.
    """
    # Priority 1: explicit <patch> tag
    m = PATCH_RE.search(text)
    if m and m.group(1).strip():
        return m.group(1).strip()
    # Priority 2: ```diff or ```patch fenced block
    m = MD_DIFF_RE.search(text)
    if m and m.group(1).strip():
        return m.group(1).strip()
    # Priority 3: raw unified diff
    m = RAW_DIFF_RE.search(text)
    if m and m.group(0).strip():
        return m.group(0).strip()
    # Priority 4: ```python (or other language) fenced block — only if it
    # looks like a substantive patch attempt (contains def/class/import or
    # is at least 100 chars). Filters out tiny snippets in <reasoning>.
    m = MD_CODE_RE.search(text)
    if m:
        body = m.group(1).strip()
        if len(body) >= 100 and any(kw in body for kw in ('def ', 'class ', 'import ', 'function ', '#include', 'package ')):
            return body
    return None


# ---- System prompt: forces tool use ----

SYSTEM_PROMPT_TEMPLATE = """You are an autonomous software engineering agent following the ReAct protocol.

You will receive a GitHub issue and repository context. Your job is to investigate the codebase via search, then propose a code patch that fixes the issue.

PROTOCOL:
- You MUST call search_code at least {min_searches} times to investigate the codebase BEFORE proposing any patch.
- Each turn, emit EXACTLY ONE tool call OR your final patch (after the minimum searches are done).
- Tool call format (use this EXACT format):
    <tool_call>{{"name": "search_code", "arguments": {{"query": "your search keyword or function name"}}}}</tool_call>
- After enough investigation, emit your final answer:
    <reasoning>your reasoning chain</reasoning>
    <patch>unified diff patch text</patch>

RULES:
- Do NOT propose a patch in your first {min_searches} turns. You must investigate first.
- Vary your search queries: do not call search_code with the same query repeatedly.
- After {max_iterations} iterations max, you must emit a final patch.
"""

INTERVENTION_PROMPT = """

[INTERVENTION] You have called search_code with the same query at least {n} times without progress. STOP repeating that search. Instead:
1. List 2 alternative file paths or function names worth searching for.
2. Pick the most promising and call search_code with a NEW query.
"""

PATCH_TOO_EARLY_REMINDER = """

[PROTOCOL VIOLATION] You proposed a patch before completing your minimum {min_searches} search calls. Patch suppressed. You have made {searches_so_far} search calls so far. Make {searches_remaining} more search_code calls to investigate the codebase, then propose a patch.
"""


def fake_tool_response(query: str, repo: str) -> str:
    """Return a deterministic short search-result stub.

    The point isn't to actually help the model fix the bug — it's to give
    the agentic loop something to react to so the iteration count and
    repeat-detection logic can do their work. A real harness would run
    the search against the repo; this stub exists so we can run at scale
    without checking out 60 repos."""
    return f"<tool_response name='search_code' query='{query}'>\n[stub] Found 3 candidate files in repo {repo}: ./module/{query.lower()}.py, ./tests/test_{query.lower()}.py, ./docs/{query.lower()}.md\nTo see file contents, search with a more specific query.\n</tool_response>\n"


def run_one_task(
    instance: Dict[str, Any],
    model: str,
    max_iterations: int,
    min_searches: int,
    min_repeats: int,
    enable_intervention: bool,
    instance_dir: Path,
) -> Dict[str, Any]:
    instance_id = instance["instance_id"]
    problem = instance["problem_statement"]
    repo = instance["repo"]

    history: List[Dict[str, Any]] = []
    query_counts: defaultdict = defaultdict(int)
    iterations = 0
    proposed_patch_text = None
    patch_suppressions = 0
    intervention_triggers = 0
    error = None

    system = SYSTEM_PROMPT_TEMPLATE.format(
        min_searches=min_searches, max_iterations=max_iterations
    )
    base = f"{system}\n\nRepository: {repo}\n\nIssue:\n{problem}\n"
    transcript = base

    for it in range(1, max_iterations + 1):
        iterations = it

        # Inject intervention if any query was repeated >= min_repeats
        if enable_intervention and any(c >= min_repeats for c in query_counts.values()):
            transcript = transcript + INTERVENTION_PROMPT.format(n=min_repeats)
            intervention_triggers += 1

        out = call_cli(transcript, model=model, timeout=600)
        history.append({
            "iteration": it,
            "prompt_len": len(transcript),
            "response": out["text"][:8000],
            "latency_s": out["latency_s"],
            "error": out["error"],
        })
        if out["error"]:
            error = out["error"]
            break

        text = out["text"]

        # Extract any tool calls
        queries = extract_search_queries(text)
        for q in queries:
            query_counts[q.lower()] += 1
        searches_so_far = sum(query_counts.values())

        # Try to extract a patch
        patch = extract_patch(text)
        if patch and searches_so_far < min_searches:
            # Patch came too early — suppress and remind
            patch_suppressions += 1
            transcript = transcript + f"\n\n<assistant>{text}</assistant>\n" \
                + PATCH_TOO_EARLY_REMINDER.format(
                    min_searches=min_searches,
                    searches_so_far=searches_so_far,
                    searches_remaining=min_searches - searches_so_far,
                ) + "\nContinue."
            continue

        if patch:
            proposed_patch_text = patch
            break

        # Append assistant turn + tool responses for any executed searches
        transcript += f"\n\n<assistant>{text}</assistant>\n"
        for q in queries:
            transcript += "\n" + fake_tool_response(q, repo)
        transcript += "\nContinue your investigation."

    result = {
        "instance_id": instance_id,
        "repo": repo,
        "model": model,
        "max_iterations": max_iterations,
        "min_searches": min_searches,
        "min_repeats": min_repeats,
        "intervention_enabled": enable_intervention,
        "iterations": iterations,
        "proposed_patch": proposed_patch_text is not None,
        "patch_len": len(proposed_patch_text) if proposed_patch_text else 0,
        "total_searches": sum(query_counts.values()),
        "unique_queries": len(query_counts),
        "max_query_repeats": max(query_counts.values()) if query_counts else 0,
        "patch_suppressions": patch_suppressions,
        "intervention_triggers": intervention_triggers,
        "query_counts": dict(query_counts),
        "error": error,
        "history": history,
    }

    instance_dir.mkdir(parents=True, exist_ok=True)
    cond = "intervention" if enable_intervention else "control"
    with open(instance_dir / f"{instance_id}_{cond}.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=60)
    p.add_argument("--model", required=True)
    p.add_argument("--max-iterations", type=int, default=8)
    p.add_argument("--min-searches", type=int, default=3,
                   help="Model must call search_code at least this many times before proposing a patch.")
    p.add_argument("--min-repeats", type=int, default=3,
                   help="Intervention triggers when any single query is repeated this many times.")
    p.add_argument("--conditions", nargs="+", default=["control", "intervention"])
    p.add_argument("--output-dir", required=True)
    p.add_argument("--exclude-ids-from", default=None)
    p.add_argument("--no-resume", action="store_true",
                   help="Disable resume; re-run instances even if per_instance JSON exists.")
    args = p.parse_args()

    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    instance_dir = out_dir / "per_instance"

    exclude_ids: List[str] = []
    if args.exclude_ids_from:
        excl_path = PROJECT_ROOT / args.exclude_ids_from
        if excl_path.exists():
            try:
                with open(excl_path) as f:
                    prior = json.load(f)
                exclude_ids = [r.get("instance_id") for r in prior.get("results", []) if r.get("instance_id")]
                print(f"Excluding {len(exclude_ids)} prior instances")
            except Exception:
                pass

    instances = load_swebench_instances(n=args.n, exclude_ids=exclude_ids)
    print(f"Loaded {len(instances)} instances")

    is_codex = (
        args.model.startswith("gpt-") or args.model.startswith("o3")
        or args.model.startswith("o4") or args.model.startswith("codex-")
        or args.model.startswith("gpt5")
    )
    is_gemini = args.model.startswith("gemini")
    if is_codex:
        cli_name = "codex"
    elif is_gemini:
        cli_name = "gemini"
    else:
        cli_name = "claude"
    cli_check = subprocess.run(["which", cli_name], capture_output=True, text=True)
    if cli_check.returncode != 0:
        print(f"ERROR: `{cli_name}` not found"); sys.exit(1)
    print(f"{cli_name} CLI: {cli_check.stdout.strip()}")
    print(f"Probing {cli_name} ...")
    probe = call_cli("Reply with only the word: ok", model=args.model, timeout=120)
    if probe["error"]:
        print(f"ERROR: probe failed: {probe['error']}"); sys.exit(1)
    print(f"  probe OK ({probe['latency_s']:.1f}s)")
    print(f"Forcing min_searches={args.min_searches}, intervention threshold={args.min_repeats}")

    all_results: List[Dict[str, Any]] = []
    t0 = time.time()
    resume_enabled = not args.no_resume
    if resume_enabled:
        # Pre-count existing per_instance files for visibility
        existing = list(instance_dir.glob("*.json"))
        if existing:
            print(f"\nRESUME: found {len(existing)} existing per_instance files; will skip those.")
    for cond in args.conditions:
        enable_intv = (cond == "intervention")
        print(f"\n=== Condition: {cond} (intervention={enable_intv}) ===")
        for i, inst in enumerate(instances, 1):
            instance_id = inst["instance_id"]
            existing_path = instance_dir / f"{instance_id}_{cond}.json"
            if resume_enabled and existing_path.exists():
                # Load the existing result and continue
                try:
                    with open(existing_path) as f:
                        r = json.load(f)
                    print(f"[{cond} {i}/{len(instances)}] {instance_id} (RESUME: skipping)", flush=True)
                    all_results.append(r)
                    continue
                except Exception as e:
                    print(f"[{cond} {i}/{len(instances)}] {instance_id} (RESUME parse failed: {e}; re-running)", flush=True)
            print(f"[{cond} {i}/{len(instances)}] {instance_id}", flush=True)
            try:
                r = run_one_task(
                    inst, args.model, args.max_iterations,
                    args.min_searches, args.min_repeats,
                    enable_intv, instance_dir,
                )
            except Exception as e:
                r = {
                    "instance_id": inst["instance_id"], "repo": inst.get("repo"),
                    "intervention_enabled": enable_intv, "iterations": 0,
                    "proposed_patch": False, "total_searches": 0,
                    "max_query_repeats": 0, "intervention_triggers": 0,
                    "patch_suppressions": 0, "error": str(e), "history": [],
                }
                print(f"  EXCEPTION: {type(e).__name__}: {e}")
            all_results.append(r)
            if i % 5 == 0:
                with open(out_dir / "results_partial.json", "w") as f:
                    json.dump({"elapsed_s": time.time() - t0,
                               "n_done": len(all_results),
                               "results": all_results}, f, indent=2)

    by_cond: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in all_results:
        cond = "intervention" if r["intervention_enabled"] else "control"
        by_cond[cond].append(r)

    summary: Dict[str, Any] = {
        "model": args.model, "n_per_condition": args.n,
        "max_iterations": args.max_iterations,
        "min_searches": args.min_searches, "min_repeats": args.min_repeats,
        "elapsed_s": time.time() - t0, "by_condition": {},
    }
    for cond, runs in by_cond.items():
        n = len(runs)
        success = sum(1 for r in runs if r["proposed_patch"])
        avg_iter = sum(r["iterations"] for r in runs) / n if n else 0
        avg_searches = sum(r["total_searches"] for r in runs) / n if n else 0
        avg_intv_trigs = sum(r.get("intervention_triggers", 0) for r in runs) / n if n else 0
        avg_patch_suppr = sum(r.get("patch_suppressions", 0) for r in runs) / n if n else 0
        max_repeat = max((r["max_query_repeats"] for r in runs), default=0)
        summary["by_condition"][cond] = {
            "n": n, "success": success, "rate": success / n if n else 0.0,
            "avg_iterations": avg_iter,
            "avg_total_searches": avg_searches,
            "avg_intervention_triggers": avg_intv_trigs,
            "avg_patch_suppressions": avg_patch_suppr,
            "max_query_repeats_observed": max_repeat,
        }

    if "control" in by_cond and "intervention" in by_cond:
        a = summary["by_condition"]["intervention"]["success"]
        b = summary["by_condition"]["intervention"]["n"] - a
        c = summary["by_condition"]["control"]["success"]
        d = summary["by_condition"]["control"]["n"] - c
        summary["fisher_exact"] = {
            "intervention_table": [a, b], "control_table": [c, d],
            "p_two_sided": fisher_exact_two_sided(a, b, c, d),
        }

    with open(out_dir / "results.json", "w") as f:
        json.dump({"summary": summary, "results": all_results}, f, indent=2)

    lines = [
        "=" * 72,
        f"B1v2: SWE-bench n={args.n} forced-tool-use via {args.model}",
        "=" * 72,
        f"Elapsed: {summary['elapsed_s']:.0f}s",
        f"Forced min_searches={args.min_searches}, intervention threshold={args.min_repeats}",
        "",
    ]
    for cond, st in summary["by_condition"].items():
        lines.append(
            f"  {cond:13s}: {st['success']}/{st['n']} ({st['rate']*100:.1f}%)  "
            f"avg_iter={st['avg_iterations']:.1f}  avg_searches={st['avg_total_searches']:.1f}  "
            f"intv_trigs={st['avg_intervention_triggers']:.2f}  patch_suppr={st['avg_patch_suppressions']:.2f}  "
            f"max_repeats={st['max_query_repeats_observed']}"
        )
    if "fisher_exact" in summary:
        fe = summary["fisher_exact"]
        lines.append("")
        lines.append(f"Fisher's exact two-sided p = {fe['p_two_sided']:.4f}")
        lines.append(f"Significant at alpha=0.05:  {fe['p_two_sided'] < 0.05}")
    text = "\n".join(lines)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(text + "\n")
    print("\n" + text)


if __name__ == "__main__":
    main()
