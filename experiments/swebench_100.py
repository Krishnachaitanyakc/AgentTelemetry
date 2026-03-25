"""SWE-bench 100+ instance case study: Larger sample for tighter CIs.

Runs the same ReAct coding agent on 100+ SWE-bench Lite instances
(up from 36 in the original study) to produce narrower confidence
intervals on the fault-type distribution.

Budget cap: $3 for API calls.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

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
from agenttelemetry.analysis import (
    AnomalyDetector, CostAggregator, DecisionAttributor, HallucinationTracer,
)

RESULTS_DIR = PROJECT_ROOT / "results" / "swebench_100"
TRACES_DIR = RESULTS_DIR / "traces"

# ---------- per-repo quotas to reach ~112 instances ----------
REPO_QUOTAS = {
    "django/django": 24,
    "sympy/sympy": 24,
    "matplotlib/matplotlib": 12,
    "scikit-learn/scikit-learn": 12,
    "pytest-dev/pytest": 10,
    "sphinx-doc/sphinx": 8,
    "astropy/astropy": 5,
    "psf/requests": 4,
    "pylint-dev/pylint": 4,
    "pydata/xarray": 4,
    "mwaskom/seaborn": 3,
    "pallets/flask": 2,
}
# Target: sum = 112

BUDGET_CAP = 3.0  # USD

SYSTEM_PROMPT = """You are a software engineering agent that diagnoses and fixes bugs in Python repositories.

Given a bug report (problem statement), you must:
1. PLAN: Analyze the problem and identify likely root causes
2. SEARCH: Look through the codebase to find relevant files and code
3. REASON: Understand why the bug occurs
4. FIX: Propose a minimal code patch that fixes the bug

You have access to these tools:
- search_code: Search the repository for relevant code patterns
- read_file: Read a specific file from the repository
- analyze_error: Analyze an error message or traceback
- propose_patch: Propose a code change to fix the bug
- verify_fix: Check if a proposed fix is logically sound

IMPORTANT: Use tools systematically. Do NOT guess. Search the code first, then reason about it.
Respond with your analysis and use tools via function calling."""


# ----------------------------------------------------------------
# Repo context extraction (from SWE-bench metadata)
# ----------------------------------------------------------------

def _extract_repo_context(instance: Dict) -> Dict[str, str]:
    """Extract searchable context from SWE-bench instance."""
    patch = instance.get("patch", "")
    files_changed = re.findall(r'^diff --git a/(.+?) b/', patch, re.MULTILINE)
    hunks = re.findall(r'^@@.*@@\n((?:[+\-\s].*\n)*)', patch, re.MULTILINE)
    code_context = "\n".join(hunks[:3]) if hunks else ""
    return {
        "files_changed": files_changed,
        "patch_preview": patch[:2000],
        "code_context": code_context[:1500],
    }


# ----------------------------------------------------------------
# Tool implementations (same as original)
# ----------------------------------------------------------------

def search_code(query: str, repo_context: Dict, tracer=None) -> str:
    results = []
    files = repo_context.get("files_changed", [])
    code = repo_context.get("code_context", "")
    query_words = query.lower().split()
    for f in files:
        score = sum(1 for w in query_words if w in f.lower())
        if score > 0:
            results.append({"file": f, "relevance": score})
    if code and any(w in code.lower() for w in query_words):
        results.append({"snippet": code[:500], "relevance": 2})
    output = json.dumps({"results": results[:5], "total": len(results)})
    with start_agent_span(
        name=f"search_code({query[:40]})",
        kind=AgentSpanKind.RETRIEVAL,
        tracer=tracer,
        attributes={
            TOOL_NAME: "search_code",
            TOOL_INPUT: query,
            TOOL_OUTPUT: output,
            TOOL_STATUS: "OK",
        },
    ):
        pass
    return output


def read_file(filepath: str, repo_context: Dict, tracer=None) -> str:
    files = repo_context.get("files_changed", [])
    patch = repo_context.get("patch_preview", "")
    found = any(filepath in f or f in filepath for f in files)
    if found and patch:
        output = json.dumps({"content": patch[:1000], "found": True})
        status = "OK"
    else:
        output = json.dumps({"error": f"File not found: {filepath}", "found": False})
        status = "ERROR"
    with start_agent_span(
        name=f"read_file({filepath[:40]})",
        kind=AgentSpanKind.TOOL_CALL,
        tracer=tracer,
        attributes={
            TOOL_NAME: "read_file",
            TOOL_INPUT: filepath,
            TOOL_OUTPUT: output,
            TOOL_STATUS: status,
        },
    ):
        pass
    return output


def analyze_error(error_msg: str, tracer=None) -> str:
    output = json.dumps({
        "analysis": f"Error involves: {error_msg[:200]}",
        "likely_cause": "See code context for details",
    })
    with start_agent_span(
        name="analyze_error",
        kind=AgentSpanKind.REASONING,
        tracer=tracer,
        attributes={
            TOOL_NAME: "analyze_error",
            TOOL_INPUT: error_msg[:200],
            TOOL_OUTPUT: output,
            REASONING_CHAIN: f"Analyzing: {error_msg[:100]}",
        },
    ):
        pass
    return output


def propose_patch(description: str, code: str, tracer=None) -> str:
    output = json.dumps({
        "patch_proposed": True,
        "description": description[:200],
        "code_preview": code[:500],
    })
    with start_agent_span(
        name="propose_patch",
        kind=AgentSpanKind.TOOL_CALL,
        tracer=tracer,
        attributes={
            TOOL_NAME: "propose_patch",
            TOOL_INPUT: description[:200],
            TOOL_OUTPUT: output,
            TOOL_STATUS: "OK",
        },
    ):
        pass
    return output


def verify_fix(patch_desc: str, tracer=None) -> str:
    output = json.dumps({
        "result": "NEEDS_REVIEW",
        "confidence": 0.6,
        "note": "Automated verification — manual review recommended",
    })
    from agenttelemetry.core.spans import GUARDRAIL_NAME, GUARDRAIL_RESULT
    with start_agent_span(
        name="verify_fix",
        kind=AgentSpanKind.GUARD_RAIL,
        tracer=tracer,
        attributes={
            GUARDRAIL_NAME: "patch_verification",
            GUARDRAIL_RESULT: "NEEDS_REVIEW",
            TOOL_OUTPUT: output,
        },
    ):
        pass
    return output


TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search the repository for code matching a query string",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the repository",
            "parameters": {
                "type": "object",
                "properties": {"filepath": {"type": "string", "description": "File path"}},
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_error",
            "description": "Analyze an error message or traceback to identify root cause",
            "parameters": {
                "type": "object",
                "properties": {"error_msg": {"type": "string", "description": "Error message"}},
                "required": ["error_msg"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_patch",
            "description": "Propose a code change to fix the bug",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "What the patch does"},
                    "code": {"type": "string", "description": "The proposed code change"},
                },
                "required": ["description", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_fix",
            "description": "Verify that a proposed fix is logically sound",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch_desc": {"type": "string", "description": "Description of the patch to verify"},
                },
                "required": ["patch_desc"],
            },
        },
    },
]


def execute_tool(name: str, args: Dict, repo_context: Dict, tracer=None) -> str:
    if name == "search_code":
        return search_code(args.get("query", ""), repo_context, tracer)
    elif name == "read_file":
        return read_file(args.get("filepath", ""), repo_context, tracer)
    elif name == "analyze_error":
        return analyze_error(args.get("error_msg", ""), tracer)
    elif name == "propose_patch":
        return propose_patch(args.get("description", ""), args.get("code", ""), tracer)
    elif name == "verify_fix":
        return verify_fix(args.get("patch_desc", ""), tracer)
    return json.dumps({"error": f"Unknown tool: {name}"})


# ----------------------------------------------------------------
# Agent runner (same as original)
# ----------------------------------------------------------------

def run_swebench_agent(
    client: OpenAI,
    instance: Dict,
    tracer=None,
    model: str = "gpt-4o-mini",
    max_iterations: int = 8,
) -> Dict[str, Any]:
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
    }

    with start_agent_span(
        name=f"swebench_agent({instance_id})",
        kind=AgentSpanKind.AGENT,
        tracer=tracer,
        attributes={
            AGENT_NAME: "swebench_agent",
            AGENT_FRAMEWORK: "agenttelemetry_swebench",
            AGENT_TASK: f"{repo}: {problem[:200]}",
        },
    ):
        with start_agent_span(
            name="plan_diagnosis",
            kind=AgentSpanKind.PLANNING,
            tracer=tracer,
            attributes={
                PLANNING_STRATEGY: "diagnose_then_fix",
                PLANNING_STEP_COUNT: 4,
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
                        REASONING_CHAIN: f"Step {iteration + 1}: Analyzing and determining next action",
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


# ----------------------------------------------------------------
# Statistical helpers
# ----------------------------------------------------------------

def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple:
    """Wilson score interval for a proportion (better for small n)."""
    if total == 0:
        return (0.0, 0.0)
    p_hat = successes / total
    denom = 1 + z**2 / total
    centre = (p_hat + z**2 / (2 * total)) / denom
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total) / denom
    return (max(0, centre - spread), min(1, centre + spread))


def bootstrap_ci(values: list, n_boot: int = 5000, alpha: float = 0.05) -> tuple:
    """Bootstrap confidence interval for a mean."""
    import random
    if not values:
        return (0.0, 0.0)
    random.seed(42)
    means = []
    for _ in range(n_boot):
        sample = random.choices(values, k=len(values))
        means.append(sum(sample) / len(sample))
    means.sort()
    lo = means[int(n_boot * alpha / 2)]
    hi = means[int(n_boot * (1 - alpha / 2))]
    return (lo, hi)


# ----------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------

def analyze_traces(all_spans: List[Dict], results: List[Dict]) -> Dict:
    """Analyze traces with confidence intervals."""
    n = len(results)
    print("\n" + "=" * 70)
    print(f"FAULT-TYPE DISTRIBUTION FROM SWE-BENCH TRACES ({n} instances)")
    print("=" * 70)

    detector = AnomalyDetector(max_retries=3, cost_threshold=0.05, token_growth_factor=1.5)
    aggregator = CostAggregator()
    attributor = DecisionAttributor()
    hallucination_tracer = HallucinationTracer(min_confidence=0.3)

    anomalies = detector.detect(all_spans)
    cost_report = aggregator.analyze(all_spans)
    decisions = attributor.analyze(all_spans)
    hallucinations = hallucination_tracer.analyze(all_spans)

    # Span kind distribution
    kind_counts = defaultdict(int)
    for s in all_spans:
        kind = s.get("agent_span_kind", "UNKNOWN") or "UNKNOWN"
        kind_counts[kind] += 1

    print(f"\n--- Span Summary ({len(all_spans)} total spans) ---")
    for kind, count in sorted(kind_counts.items(), key=lambda x: -x[1]):
        pct = count / len(all_spans) * 100
        print(f"  {kind:<15} {count:>5} ({pct:>5.1f}%)")

    # Anomaly distribution
    print(f"\n--- Anomalies Detected ({len(anomalies)}) ---")
    anomaly_types = defaultdict(int)
    for a in anomalies:
        anomaly_types[a.anomaly_type.value] += 1

    for atype, count in sorted(anomaly_types.items(), key=lambda x: -x[1]):
        print(f"  {atype:<25} {count}")
    if not anomalies:
        print("  (none detected)")

    # Cost analysis
    print(f"\n--- Cost Analysis ---")
    print(f"  Total cost: ${cost_report.total_cost:.4f}")
    print(f"  Total tokens: {cost_report.total_input_tokens} in / {cost_report.total_output_tokens} out")
    for model, mc in cost_report.by_model.items():
        print(f"  {model}: ${mc.cost:.4f} ({mc.call_count} calls)")

    # Tool decision analysis
    print(f"\n--- Tool Decision Attribution ({len(decisions)}) ---")
    tool_counts = defaultdict(int)
    for d in decisions:
        tool_counts[d.tool_name] += 1
    for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
        print(f"  {tool:<20} {count} calls")

    # Hallucination candidates
    print(f"\n--- Hallucination Candidates ({len(hallucinations)}) ---")
    for h in hallucinations[:5]:
        print(f"  [{h.confidence:.2f}] {h.claim[:60]}...")

    # ---- Failure mode classification ----
    print(f"\n--- Failure Mode Classification ---")
    failed = [r for r in results if r.get("error") or not r.get("proposed_patch")]
    succeeded = [r for r in results if r.get("proposed_patch") and not r.get("error")]
    max_iter = [r for r in results if r.get("error") == "max_iterations_reached"]

    print(f"  Total instances: {n}")
    print(f"  Proposed patch: {len(succeeded)}")
    print(f"  No patch proposed: {len([r for r in results if not r.get('proposed_patch')])}")
    print(f"  Max iterations (reasoning loop): {len(max_iter)}")
    print(f"  Errors: {len([r for r in results if r.get('error') and r['error'] != 'max_iterations_reached'])}")
    print(f"  Used verify_fix: {len([r for r in results if r.get('verified')])}")

    # Fault-type distribution
    fault_distribution = {
        "reasoning_loop": 0,
        "context_overflow": 0,
        "planning_failure": 0,
        "infinite_retry": 0,
        "missing_guardrail": 0,
        "cost_explosion": 0,
        "tool_failure": 0,
    }

    fault_distribution["reasoning_loop"] = len(max_iter)
    fault_distribution["context_overflow"] = anomaly_types.get("context_overflow", 0)
    fault_distribution["infinite_retry"] = anomaly_types.get("infinite_retry", 0)
    fault_distribution["cost_explosion"] = anomaly_types.get("cost_explosion", 0)
    unverified = [r for r in results if r.get("proposed_patch") and not r.get("verified")]
    fault_distribution["missing_guardrail"] = len(unverified)
    no_tools = [r for r in results if len(r.get("tool_calls", [])) == 0]
    fault_distribution["planning_failure"] = len(no_tools)
    tool_errors = sum(1 for s in all_spans
                      if s.get("agent_span_kind") == "TOOL_CALL"
                      and (s.get("attributes") or {}).get("tool.status") == "ERROR")
    fault_distribution["tool_failure"] = tool_errors

    print(f"\n--- Fault Type Distribution (AgentTelemetry taxonomy) ---")
    for fault, count in sorted(fault_distribution.items(), key=lambda x: -x[1]):
        if count > 0:
            pct = count / max(n, 1) * 100
            lo, hi = wilson_ci(count, n)
            print(f"  {fault:<25} {count:>3} ({pct:>5.1f}%)  95% CI: [{lo*100:.1f}%, {hi*100:.1f}%]")

    # Reasoning loop rate with CI
    rl_count = fault_distribution["reasoning_loop"]
    rl_pct = rl_count / n * 100
    rl_lo, rl_hi = wilson_ci(rl_count, n)
    print(f"\n--- Reasoning Loop Rate ---")
    print(f"  {rl_count}/{n} = {rl_pct:.1f}%  95% CI: [{rl_lo*100:.1f}%, {rl_hi*100:.1f}%]")

    # Patch rate with CI
    patch_count = len(succeeded)
    patch_pct = patch_count / n * 100
    p_lo, p_hi = wilson_ci(patch_count, n)
    print(f"\n--- Patch Rate ---")
    print(f"  {patch_count}/{n} = {patch_pct:.1f}%  95% CI: [{p_lo*100:.1f}%, {p_hi*100:.1f}%]")

    # Per-repo breakdown
    print(f"\n--- Per-Repo Breakdown ---")
    repo_results = defaultdict(lambda: {"total": 0, "patch": 0, "loop": 0})
    for r in results:
        repo = r.get("repo", "unknown")
        repo_results[repo]["total"] += 1
        if r.get("proposed_patch") and not r.get("error"):
            repo_results[repo]["patch"] += 1
        if r.get("error") == "max_iterations_reached":
            repo_results[repo]["loop"] += 1
    for repo, rr in sorted(repo_results.items()):
        p_rate = rr["patch"] / rr["total"] * 100 if rr["total"] else 0
        l_rate = rr["loop"] / rr["total"] * 100 if rr["total"] else 0
        print(f"  {repo:<35} {rr['total']:>3} instances  patch={p_rate:.0f}%  loop={l_rate:.0f}%")

    # Span kinds essential for detection
    print(f"\n--- Span Kinds Essential for Detection ---")
    essential = {
        "REASONING": ["reasoning_loop"],
        "LLM_CALL": ["context_overflow", "cost_explosion"],
        "TOOL_CALL": ["infinite_retry", "tool_failure"],
        "GUARD_RAIL": ["missing_guardrail"],
        "PLANNING": ["planning_failure"],
    }
    for kind, faults in essential.items():
        detected = sum(fault_distribution.get(f, 0) for f in faults)
        if detected > 0:
            active = [f for f in faults if fault_distribution.get(f, 0) > 0]
            print(f"  {kind:<15} -> detected {detected} faults ({', '.join(active)})")

    # Comparison with 36-instance study
    print(f"\n--- Comparison with Original 36-Instance Study ---")
    print(f"  Original reasoning loop rate: 67% (24/36)")
    print(f"  Current  reasoning loop rate: {rl_pct:.1f}% ({rl_count}/{n})")
    print(f"  Original patch rate: 33% (12/36)")
    print(f"  Current  patch rate: {patch_pct:.1f}% ({patch_count}/{n})")
    diff_rl = abs(rl_pct - 67)
    diff_patch = abs(patch_pct - 33)
    if diff_rl < 10 and diff_patch < 10:
        print(f"  -> CONSISTENT: Both rates within 10 pp of original study")
    else:
        print(f"  -> DIVERGENT: RL diff={diff_rl:.1f}pp, Patch diff={diff_patch:.1f}pp")

    # Mean iterations with CI
    iter_values = [r["iterations"] for r in results if r.get("iterations")]
    if iter_values:
        mean_iter = sum(iter_values) / len(iter_values)
        ci_lo, ci_hi = bootstrap_ci(iter_values)
        print(f"\n--- Iteration Statistics ---")
        print(f"  Mean iterations: {mean_iter:.2f}  95% CI: [{ci_lo:.2f}, {ci_hi:.2f}]")

    analysis = {
        "n_instances": n,
        "span_summary": dict(kind_counts),
        "total_spans": len(all_spans),
        "anomalies": len(anomalies),
        "anomaly_types": dict(anomaly_types),
        "fault_distribution": fault_distribution,
        "total_cost": cost_report.total_cost,
        "hallucination_candidates": len(hallucinations),
        "tool_decisions": len(decisions),
        "patches_proposed": len(succeeded),
        "patch_rate": patch_pct,
        "patch_rate_ci": [p_lo * 100, p_hi * 100],
        "reasoning_loop_rate": rl_pct,
        "reasoning_loop_ci": [rl_lo * 100, rl_hi * 100],
        "per_repo": {
            repo: {"total": rr["total"], "patch": rr["patch"], "loop": rr["loop"]}
            for repo, rr in repo_results.items()
        },
    }
    return analysis


# ----------------------------------------------------------------
# Instance selection
# ----------------------------------------------------------------

def select_instances(ds) -> list:
    """Select ~112 instances spread across all 12 repos."""
    repos = defaultdict(list)
    for i, inst in enumerate(ds):
        repos[inst["repo"]].append(i)

    selected = []
    for repo, quota in REPO_QUOTAS.items():
        indices = repos.get(repo, [])
        # Spread evenly: take every Nth instance
        if len(indices) <= quota:
            chosen = indices
        else:
            step = len(indices) / quota
            chosen = [indices[int(i * step)] for i in range(quota)]
        selected.extend(chosen)
        print(f"  {repo:<35} {len(chosen):>3}/{len(indices)} instances")

    print(f"  {'TOTAL':<35} {len(selected):>3} instances across {len(REPO_QUOTAS)} repos")
    return selected


# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------

def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("AgentTelemetry SWE-bench 100+ Instance Case Study")
    print("=" * 70)

    # Load SWE-bench Lite
    print("\nLoading SWE-bench Lite dataset...")
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    print(f"  {len(ds)} instances available")

    # Select instances
    print("\nSelecting instances (quota per repo):")
    selected_indices = select_instances(ds)

    # Setup
    client = OpenAI()
    provider = AgentTelemetryProvider(
        service_name="swebench_100_study",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(str(TRACES_DIR / "swebench_100_traces.jsonl"))
    provider.setup(set_global=True)
    tracer = provider.get_tracer("swebench")

    results = []
    total_cost = 0.0

    print(f"\nRunning agent on {len(selected_indices)} instances (model: gpt-4o-mini, budget: ${BUDGET_CAP})...")
    print("-" * 70)

    for idx_num, ds_idx in enumerate(selected_indices):
        instance = ds[ds_idx]
        instance_id = instance["instance_id"]
        repo = instance["repo"]

        print(f"  [{idx_num+1:>3}/{len(selected_indices)}] {instance_id[:55]}...", end=" ", flush=True)

        try:
            result = run_swebench_agent(
                client, instance, tracer=tracer, model="gpt-4o-mini",
            )
            results.append(result)
            inst_cost = estimate_cost(
                "gpt-4o-mini",
                result["total_input_tokens"],
                result["total_output_tokens"],
            )
            total_cost += inst_cost

            tools = ",".join(result["tool_calls"][:4])
            patch = "PATCH" if result["proposed_patch"] else "NO_PATCH"
            verified = "+V" if result["verified"] else ""
            err = f" ERR:{result['error'][:15]}" if result.get("error") else ""
            print(f"{patch}{verified} ({result['iterations']}it, ${inst_cost:.3f}){err}")

        except Exception as e:
            print(f"CRASH: {e}")
            results.append({
                "instance_id": instance_id,
                "repo": repo,
                "error": str(e),
                "tool_calls": [],
                "iterations": 0,
            })

        time.sleep(0.15)  # Rate limiting

        # Budget guard
        if total_cost > BUDGET_CAP:
            print(f"\n  BUDGET CAP: ${total_cost:.2f} spent (limit: ${BUDGET_CAP}), stopping")
            break

    provider.shutdown()

    # Save results
    with open(RESULTS_DIR / "agent_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n  Total cost: ${total_cost:.4f}")
    print(f"  Results saved: {len(results)} instances")

    # Load all spans and analyze
    all_spans = json_exporter.get_exported_spans()
    print(f"  Total spans: {len(all_spans)}")

    analysis = analyze_traces(all_spans, results)

    with open(RESULTS_DIR / "analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"\n{'=' * 70}")
    print(f"SWE-BENCH 100+ CASE STUDY COMPLETE")
    print(f"  Instances: {len(results)}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"  Results: {RESULTS_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
