"""Simulated user study: 6 developer personas debug agent failures
with and without AgentTelemetry span kinds.

For each of 6 failed SWE-bench traces, 6 developer personas attempt to
diagnose the root cause under two conditions:
  (a) AgentTelemetry view  -- spans carry all 9 semantic kind labels
  (b) Vanilla OTel view    -- all spans shown as generic "INTERNAL"

Each diagnosis is performed by an LLM call (GPT-4o-mini) role-playing
the persona.  We measure:
  - Correct diagnosis (does the persona identify the root cause?)
  - Spans examined (how many spans does the persona report inspecting?)

Budget: ~$2 max (6 personas x 6 traces x 2 conditions = 72 LLM calls).

Usage:
    cd /path/to/agenttelemetry
    export $(grep -v '^#' .env | xargs)
    PYTHONPATH=src .venv/bin/python3.12 experiments/simulated_user_study.py
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESULTS_DIR = PROJECT_ROOT / "results" / "swebench_100"
TRACES_FILE = RESULTS_DIR / "traces" / "swebench_100_traces.jsonl"
AGENT_RESULTS_FILE = RESULTS_DIR / "agent_results.json"
OUTPUT_DIR = PROJECT_ROOT / "results" / "simulated_user_study"

MODEL = "gpt-4o-mini"
BUDGET_CAP = 2.00  # USD

# Cost per token for gpt-4o-mini (as of 2025)
COST_PER_INPUT_TOKEN = 0.15 / 1_000_000   # $0.15 per 1M input tokens
COST_PER_OUTPUT_TOKEN = 0.60 / 1_000_000  # $0.60 per 1M output tokens

# ---------------------------------------------------------------------------
# 6 Developer Personas
# ---------------------------------------------------------------------------

PERSONAS = [
    {
        "id": "junior_dev",
        "label": "Junior Dev",
        "description": (
            "You are a junior software developer with 2 years of experience. "
            "You are unfamiliar with AI agents and distributed tracing. "
            "You understand basic programming concepts but have never debugged "
            "an agent system before. You tend to examine spans one-by-one "
            "from the beginning."
        ),
    },
    {
        "id": "senior_backend",
        "label": "Sr. Backend",
        "description": (
            "You are a senior backend engineer with 8 years of experience. "
            "You are very familiar with distributed tracing (Jaeger, Zipkin, "
            "OpenTelemetry) and microservice debugging. You know how to use "
            "span hierarchies and filtering to quickly narrow down issues. "
            "You have some familiarity with LLM-based applications."
        ),
    },
    {
        "id": "ml_engineer",
        "label": "ML Engineer",
        "description": (
            "You are an ML engineer with 5 years of experience who builds "
            "AI agents daily. You understand LLM reasoning loops, prompt "
            "engineering, and common agent failure modes like infinite loops, "
            "hallucinations, and context overflow. You know what to look for "
            "in agent traces."
        ),
    },
    {
        "id": "sre_devops",
        "label": "SRE/DevOps",
        "description": (
            "You are an SRE/DevOps engineer with 6 years of experience "
            "monitoring production systems. You are expert at reading "
            "telemetry data, dashboards, and traces. You look for patterns "
            "like repeated operations, increasing latency, and resource "
            "exhaustion. You are less familiar with AI-specific failure modes."
        ),
    },
    {
        "id": "qa_engineer",
        "label": "QA Engineer",
        "description": (
            "You are a QA engineer with 4 years of experience specializing "
            "in testing complex systems. You are methodical and examine "
            "traces systematically. You look for unexpected patterns, missing "
            "steps, and deviations from expected behavior. You have moderate "
            "familiarity with AI systems."
        ),
    },
    {
        "id": "tech_lead",
        "label": "Tech Lead",
        "description": (
            "You are a tech lead with 10 years of experience who reviews "
            "agent system architectures. You understand both the distributed "
            "systems and the AI/ML aspects. You can quickly identify "
            "architectural issues and know common pitfalls in agent design. "
            "You efficiently skip irrelevant spans."
        ),
    },
]

# ---------------------------------------------------------------------------
# Known root causes for the 6 selected traces (ground truth)
# All 6 are reasoning-loop failures (max_iterations_reached).
# We accept several phrasings as correct.
# ---------------------------------------------------------------------------

CORRECT_DIAGNOSIS_PATTERNS = [
    r"reasoning\s*loop",
    r"infinite\s*loop",
    r"max.?iteration",
    r"stuck\s+in\s+a?\s*loop",
    r"repeated\s+(search|tool|action|call)",
    r"keeps?\s+(searching|repeating|looping|calling)",
    r"never\s+(propos|converge|reach|generat)",
    r"circular",
    r"no\s+progress",
    r"same\s+(tools?|actions?|search)\s+(over|again|repeat)",
    r"repetitive",
    r"did\s+not\s+(propose|produce|generate)\s+(a\s+)?(patch|fix|solution)",
    r"loop\s+without\s+(progress|resolution|fix)",
    r"unable\s+to\s+(break|escape|exit)\s+(the\s+)?(loop|cycle)",
    r"exhausted\s+(all\s+)?iteration",
    r"spinning",
]

# ---------------------------------------------------------------------------
# Load and prepare trace data
# ---------------------------------------------------------------------------

def load_traces() -> List[Dict[str, Any]]:
    """Load all spans from the JSONL trace file."""
    spans = []
    with open(TRACES_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                spans.append(json.loads(line))
    return spans


def load_agent_results() -> List[Dict[str, Any]]:
    with open(AGENT_RESULTS_FILE) as f:
        return json.load(f)


def group_by_trace(spans: List[Dict]) -> Dict[str, List[Dict]]:
    traces: Dict[str, List[Dict]] = defaultdict(list)
    for span in spans:
        traces[span.get("trace_id", "unknown")].append(span)
    for tid in traces:
        traces[tid].sort(key=lambda s: s.get("start_time_ns", 0) or 0)
    return dict(traces)


def build_instance_to_trace(
    traces: Dict[str, List[Dict]],
) -> Dict[str, str]:
    """Map instance_id -> trace_id via AGENT span names."""
    mapping: Dict[str, str] = {}
    for tid, spans in traces.items():
        for span in spans:
            if span.get("agent_span_kind") == "AGENT":
                name = span.get("name", "")
                if "(" in name and ")" in name:
                    inst_id = name[name.index("(") + 1 : name.index(")")]
                    mapping[inst_id] = tid
                break
    return mapping


def select_traces(
    results: List[Dict],
    instance_to_trace: Dict[str, str],
    n: int = 6,
) -> List[Dict]:
    """Select n diverse failed traces across different repos."""
    failed = [
        r for r in results
        if r.get("error") == "max_iterations_reached"
        and r["instance_id"] in instance_to_trace
    ]
    seen_repos = set()
    selected = []
    # First pass: one per repo for diversity
    for r in failed:
        repo = r["repo"]
        if repo not in seen_repos and len(selected) < n:
            seen_repos.add(repo)
            selected.append(r)
    # Fill remaining slots
    for r in failed:
        if r not in selected and len(selected) < n:
            selected.append(r)
    return selected[:n]


# ---------------------------------------------------------------------------
# Render traces for the two conditions
# ---------------------------------------------------------------------------

def render_agenttelemetry_trace(spans: List[Dict]) -> str:
    """Render a trace with AgentTelemetry span kind labels."""
    lines = []
    lines.append("=== AGENT TRACE (AgentTelemetry instrumented) ===")
    lines.append(f"Total spans: {len(spans)}")
    lines.append("")

    # Summary by kind
    kinds = defaultdict(int)
    for s in spans:
        kinds[s.get("agent_span_kind", "UNKNOWN")] += 1
    lines.append("Span kind summary:")
    for k, c in sorted(kinds.items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {c}")
    lines.append("")

    # Each span with kind label
    for i, s in enumerate(spans, 1):
        kind = s.get("agent_span_kind", "UNKNOWN")
        name = s.get("name", "unnamed")
        dur = s.get("duration_ms", 0)
        attrs = s.get("attributes", {})

        line = f"[Span {i:>2}] Kind={kind:<12} Name={name}"
        if dur and dur > 1:
            line += f"  ({dur:.0f}ms)"
        lines.append(line)

        # Show key attributes based on kind
        if kind == "REASONING":
            chain = attrs.get("reasoning.chain", "")
            if chain:
                lines.append(f"         Reasoning: {chain[:120]}")
        elif kind == "LLM_CALL":
            model = attrs.get("llm.model", "")
            in_tok = attrs.get("llm.input_tokens", 0)
            out_tok = attrs.get("llm.output_tokens", 0)
            cost = attrs.get("llm.cost", 0)
            lines.append(f"         Model={model} tokens={in_tok}/{out_tok} cost=${cost:.4f}" if cost else
                         f"         Model={model} tokens={in_tok}/{out_tok}")
        elif kind == "TOOL_CALL":
            tool = attrs.get("tool.name", "")
            status = attrs.get("tool.status", "")
            inp = attrs.get("tool.input", "")[:80] if attrs.get("tool.input") else ""
            lines.append(f"         Tool={tool} Status={status} Input={inp}")
        elif kind == "RETRIEVAL":
            tool = attrs.get("tool.name", "")
            inp = attrs.get("tool.input", "")[:80] if attrs.get("tool.input") else ""
            lines.append(f"         Tool={tool} Query={inp}")
        elif kind == "PLANNING":
            strategy = attrs.get("planning.strategy", "")
            steps = attrs.get("planning.step_count", "")
            lines.append(f"         Strategy={strategy} Steps={steps}")
        elif kind == "MEMORY":
            op = attrs.get("memory.operation", "")
            key = attrs.get("memory.key", "")
            lines.append(f"         Op={op} Key={key}")
        elif kind == "GUARD_RAIL":
            name_gr = attrs.get("guardrail.name", "")
            result_gr = attrs.get("guardrail.result", "")
            lines.append(f"         Guardrail={name_gr} Result={result_gr}")
        elif kind == "AGENT":
            framework = attrs.get("agent.framework", "")
            task = attrs.get("agent.task", "")[:120] if attrs.get("agent.task") else ""
            lines.append(f"         Framework={framework}")
            if task:
                lines.append(f"         Task={task}")

    return "\n".join(lines)


def render_vanilla_otel_trace(spans: List[Dict]) -> str:
    """Render the same trace but with all spans as INTERNAL (no kind labels)."""
    lines = []
    lines.append("=== AGENT TRACE (Standard OpenTelemetry / vanilla OTel) ===")
    lines.append(f"Total spans: {len(spans)}")
    lines.append("")
    lines.append("Note: All spans have kind=INTERNAL (OpenTelemetry default).")
    lines.append("No agent-specific span kind labels are available.")
    lines.append("")

    for i, s in enumerate(spans, 1):
        name = s.get("name", "unnamed")
        dur = s.get("duration_ms", 0)
        attrs = s.get("attributes", {})

        line = f"[Span {i:>2}] Kind=INTERNAL     Name={name}"
        if dur and dur > 1:
            line += f"  ({dur:.0f}ms)"
        lines.append(line)

        # Show raw attributes without kind-based organization
        shown_attrs = {}
        for k, v in attrs.items():
            # Strip the agenttelemetry.span.kind attribute
            if k == "agenttelemetry.span.kind":
                continue
            if v and str(v).strip():
                shown_attrs[k] = str(v)[:100]

        if shown_attrs:
            # Show up to 3 attributes as flat key-value pairs
            for j, (k, v) in enumerate(list(shown_attrs.items())[:3]):
                lines.append(f"         {k}={v}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM-based diagnosis simulation
# ---------------------------------------------------------------------------

def build_diagnosis_prompt(
    persona_desc: str,
    trace_text: str,
    instance_id: str,
) -> str:
    """Build the prompt for a persona debugging a trace."""
    return f"""You are debugging an AI agent that failed to complete its task.

YOUR BACKGROUND:
{persona_desc}

CONTEXT:
The agent was tasked with diagnosing and fixing a bug in an open-source Python repository
(SWE-bench instance: {instance_id}). The agent had access to tools: search_code, read_file,
analyze_error, propose_patch, verify_fix. The agent was given 8 iterations maximum.

The agent FAILED to complete its task. Your job is to examine the trace below and determine:
1. What is the root cause of the agent's failure?
2. How many spans did you need to examine before you could confidently identify the root cause?

TRACE:
{trace_text}

INSTRUCTIONS:
- Examine the trace carefully, as your persona would.
- State the root cause of failure clearly and concisely.
- Report exactly how many spans you examined to reach your diagnosis.
- Be specific: name the failure pattern (e.g., "reasoning loop", "tool error", "context overflow", etc.)

Respond in this EXACT format:
ROOT_CAUSE: <your diagnosis in 1-2 sentences>
SPANS_EXAMINED: <integer number of spans you examined>
CONFIDENCE: <HIGH/MEDIUM/LOW>
REASONING: <brief explanation of how you reached your diagnosis>"""


def diagnose_with_llm(
    client: OpenAI,
    persona: Dict,
    trace_text: str,
    instance_id: str,
) -> Dict[str, Any]:
    """Call GPT-4o-mini to simulate a persona diagnosing a trace."""
    prompt = build_diagnosis_prompt(
        persona["description"], trace_text, instance_id
    )

    start = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are role-playing as a developer debugging an AI agent failure. Follow the instructions exactly."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
        temperature=0.3,  # Low but not zero for persona variation
    )
    latency = time.time() - start

    usage = response.usage
    cost = (
        usage.prompt_tokens * COST_PER_INPUT_TOKEN
        + usage.completion_tokens * COST_PER_OUTPUT_TOKEN
    )
    content = response.choices[0].message.content or ""

    # Parse structured response
    root_cause = ""
    spans_examined = 0
    confidence = ""
    reasoning = ""

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("ROOT_CAUSE:"):
            root_cause = line[len("ROOT_CAUSE:"):].strip()
        elif line.startswith("SPANS_EXAMINED:"):
            try:
                spans_examined = int(re.search(r'\d+', line).group())
            except (AttributeError, ValueError):
                spans_examined = -1
        elif line.startswith("CONFIDENCE:"):
            confidence = line[len("CONFIDENCE:"):].strip()
        elif line.startswith("REASONING:"):
            reasoning = line[len("REASONING:"):].strip()

    # Check if diagnosis is correct
    diagnosis_text = f"{root_cause} {reasoning}".lower()
    correct = any(
        re.search(pat, diagnosis_text) for pat in CORRECT_DIAGNOSIS_PATTERNS
    )

    return {
        "persona_id": persona["id"],
        "persona_label": persona["label"],
        "root_cause": root_cause,
        "spans_examined": spans_examined,
        "confidence": confidence,
        "reasoning": reasoning,
        "correct": correct,
        "raw_response": content,
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "cost": cost,
        "latency_s": latency,
    }


# ---------------------------------------------------------------------------
# Check diagnosis correctness
# ---------------------------------------------------------------------------

def is_correct(diagnosis: Dict) -> bool:
    return diagnosis.get("correct", False)


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def mean_or_zero(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def wilson_ci(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a proportion."""
    if total == 0:
        return (0.0, 0.0)
    p_hat = successes / total
    denom = 1 + z ** 2 / total
    centre = (p_hat + z ** 2 / (2 * total)) / denom
    spread = z * (((p_hat * (1 - p_hat) + z ** 2 / (4 * total)) / total) ** 0.5) / denom
    return (max(0, centre - spread), min(1, centre + spread))


def bootstrap_ci(
    values: List[float], n_boot: int = 5000, alpha: float = 0.05
) -> Tuple[float, float]:
    import random
    if not values:
        return (0.0, 0.0)
    random.seed(42)
    means = sorted(
        statistics.mean(random.choices(values, k=len(values)))
        for _ in range(n_boot)
    )
    lo = means[int(n_boot * alpha / 2)]
    hi = means[int(n_boot * (1 - alpha / 2))]
    return (lo, hi)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    if not TRACES_FILE.exists():
        print(f"ERROR: Trace file not found: {TRACES_FILE}")
        sys.exit(1)
    if not AGENT_RESULTS_FILE.exists():
        print(f"ERROR: Agent results not found: {AGENT_RESULTS_FILE}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("SIMULATED USER STUDY: Developer Debugging with AgentTelemetry")
    print("=" * 72)

    # ---- Load data ----
    print("\nLoading SWE-bench traces...")
    all_spans = load_traces()
    results = load_agent_results()
    traces = group_by_trace(all_spans)
    instance_to_trace = build_instance_to_trace(traces)

    print(f"  {len(all_spans)} spans, {len(traces)} traces, {len(results)} results")

    # ---- Select 6 diverse failed traces ----
    selected = select_traces(results, instance_to_trace, n=6)
    print(f"\nSelected {len(selected)} failed traces from {len(set(r['repo'] for r in selected))} repos:")
    for r in selected:
        tid = instance_to_trace[r["instance_id"]]
        n_spans = len(traces[tid])
        print(f"  {r['instance_id']:50s}  repo={r['repo']:30s}  spans={n_spans}")

    # ---- Prepare trace renderings ----
    print("\nRendering traces (2 conditions x 6 traces)...")
    rendered = {}
    for r in selected:
        tid = instance_to_trace[r["instance_id"]]
        trace_spans = traces[tid]
        rendered[r["instance_id"]] = {
            "agenttelemetry": render_agenttelemetry_trace(trace_spans),
            "vanilla_otel": render_vanilla_otel_trace(trace_spans),
            "n_spans": len(trace_spans),
        }

    # ---- Run simulated diagnoses ----
    client = OpenAI()
    total_cost = 0.0
    all_diagnoses: List[Dict] = []

    n_total = len(PERSONAS) * len(selected) * 2
    print(f"\nRunning {n_total} LLM calls ({len(PERSONAS)} personas x {len(selected)} traces x 2 conditions)...")
    print(f"Model: {MODEL}, Budget: ${BUDGET_CAP}")
    print("-" * 72)

    call_num = 0
    for condition in ["agenttelemetry", "vanilla_otel"]:
        cond_label = "AgentTelemetry" if condition == "agenttelemetry" else "Vanilla OTel"
        for r in selected:
            instance_id = r["instance_id"]
            trace_text = rendered[instance_id][condition]

            for persona in PERSONAS:
                call_num += 1
                print(
                    f"  [{call_num:>2}/{n_total}] {cond_label:16s} | "
                    f"{persona['label']:12s} | {instance_id[:35]}...",
                    end=" ",
                    flush=True,
                )

                try:
                    diag = diagnose_with_llm(
                        client, persona, trace_text, instance_id
                    )
                    diag["condition"] = condition
                    diag["condition_label"] = cond_label
                    diag["instance_id"] = instance_id
                    diag["repo"] = r["repo"]
                    diag["n_trace_spans"] = rendered[instance_id]["n_spans"]

                    total_cost += diag["cost"]
                    all_diagnoses.append(diag)

                    correct_str = "CORRECT" if diag["correct"] else "WRONG"
                    print(
                        f"{correct_str:>7} spans={diag['spans_examined']:>2} "
                        f"(${diag['cost']:.4f})"
                    )

                except Exception as e:
                    print(f"ERROR: {e}")
                    all_diagnoses.append({
                        "persona_id": persona["id"],
                        "persona_label": persona["label"],
                        "condition": condition,
                        "condition_label": cond_label,
                        "instance_id": instance_id,
                        "repo": r["repo"],
                        "correct": False,
                        "spans_examined": -1,
                        "error": str(e),
                        "cost": 0,
                    })

                time.sleep(0.1)  # Rate limiting

                if total_cost > BUDGET_CAP:
                    print(f"\n  BUDGET CAP: ${total_cost:.2f} spent")
                    break
            if total_cost > BUDGET_CAP:
                break
        if total_cost > BUDGET_CAP:
            break

    print(f"\n  Total LLM calls: {call_num}")
    print(f"  Total cost: ${total_cost:.4f}")

    # ---- Analyze results ----
    print("\n" + "=" * 72)
    print("RESULTS ANALYSIS")
    print("=" * 72)

    at_diags = [d for d in all_diagnoses if d["condition"] == "agenttelemetry"]
    otel_diags = [d for d in all_diagnoses if d["condition"] == "vanilla_otel"]

    # Accuracy by condition
    at_correct = sum(1 for d in at_diags if d.get("correct"))
    otel_correct = sum(1 for d in otel_diags if d.get("correct"))
    at_total = len(at_diags)
    otel_total = len(otel_diags)

    at_acc = at_correct / at_total * 100 if at_total else 0
    otel_acc = otel_correct / otel_total * 100 if otel_total else 0

    at_ci = wilson_ci(at_correct, at_total)
    otel_ci = wilson_ci(otel_correct, otel_total)

    print(f"\n--- Diagnostic Accuracy ---")
    print(f"  AgentTelemetry: {at_correct}/{at_total} = {at_acc:.1f}%  "
          f"95% CI [{at_ci[0]*100:.1f}%, {at_ci[1]*100:.1f}%]")
    print(f"  Vanilla OTel:   {otel_correct}/{otel_total} = {otel_acc:.1f}%  "
          f"95% CI [{otel_ci[0]*100:.1f}%, {otel_ci[1]*100:.1f}%]")
    if otel_acc > 0:
        print(f"  Improvement: {at_acc - otel_acc:+.1f} percentage points")

    # Spans examined by condition
    at_spans = [d["spans_examined"] for d in at_diags if d.get("spans_examined", -1) > 0]
    otel_spans = [d["spans_examined"] for d in otel_diags if d.get("spans_examined", -1) > 0]

    at_spans_mean = mean_or_zero(at_spans)
    otel_spans_mean = mean_or_zero(otel_spans)
    at_spans_ci = bootstrap_ci([float(v) for v in at_spans])
    otel_spans_ci = bootstrap_ci([float(v) for v in otel_spans])

    print(f"\n--- Spans Examined ---")
    print(f"  AgentTelemetry: mean={at_spans_mean:.1f}  "
          f"95% CI [{at_spans_ci[0]:.1f}, {at_spans_ci[1]:.1f}]")
    print(f"  Vanilla OTel:   mean={otel_spans_mean:.1f}  "
          f"95% CI [{otel_spans_ci[0]:.1f}, {otel_spans_ci[1]:.1f}]")
    if otel_spans_mean > 0:
        reduction = (1 - at_spans_mean / otel_spans_mean) * 100
        print(f"  Reduction: {reduction:.1f}%")
    else:
        reduction = 0.0

    # Per-persona breakdown
    print(f"\n--- Per-Persona Results ---")
    print(f"  {'Persona':<14} {'AT Acc':>7} {'OTel Acc':>9} "
          f"{'AT Spans':>9} {'OTel Spans':>11}")
    print(f"  {'-'*14} {'-'*7} {'-'*9} {'-'*9} {'-'*11}")

    persona_results = {}
    for persona in PERSONAS:
        pid = persona["id"]
        p_at = [d for d in at_diags if d["persona_id"] == pid]
        p_otel = [d for d in otel_diags if d["persona_id"] == pid]

        p_at_correct = sum(1 for d in p_at if d.get("correct"))
        p_otel_correct = sum(1 for d in p_otel if d.get("correct"))
        p_at_total = len(p_at)
        p_otel_total = len(p_otel)

        p_at_acc = p_at_correct / p_at_total * 100 if p_at_total else 0
        p_otel_acc = p_otel_correct / p_otel_total * 100 if p_otel_total else 0

        p_at_spans = mean_or_zero(
            [d["spans_examined"] for d in p_at if d.get("spans_examined", -1) > 0]
        )
        p_otel_spans = mean_or_zero(
            [d["spans_examined"] for d in p_otel if d.get("spans_examined", -1) > 0]
        )

        print(f"  {persona['label']:<14} {p_at_acc:>6.0f}% {p_otel_acc:>8.0f}% "
              f"{p_at_spans:>9.1f} {p_otel_spans:>11.1f}")

        persona_results[pid] = {
            "label": persona["label"],
            "at_accuracy": p_at_acc,
            "otel_accuracy": p_otel_acc,
            "at_spans_examined": p_at_spans,
            "otel_spans_examined": p_otel_spans,
            "at_correct": p_at_correct,
            "at_total": p_at_total,
            "otel_correct": p_otel_correct,
            "otel_total": p_otel_total,
        }

    # Full results table
    print(f"\n--- Full Results Table ---")
    print(f"  {'Persona':<14} {'Condition':<16} {'Correct':>8} {'Spans':>6}")
    print(f"  {'-'*14} {'-'*16} {'-'*8} {'-'*6}")
    for d in sorted(all_diagnoses, key=lambda x: (x["persona_id"], x["condition"])):
        correct_str = "Yes" if d.get("correct") else "No"
        spans = d.get("spans_examined", -1)
        spans_str = str(spans) if spans > 0 else "N/A"
        print(f"  {d['persona_label']:<14} {d['condition_label']:<16} {correct_str:>8} {spans_str:>6}")

    # Effect sizes
    print(f"\n--- Effect Sizes ---")
    # Cohen's h for proportions
    import math
    if at_total > 0 and otel_total > 0:
        p1 = at_correct / at_total
        p2 = otel_correct / otel_total
        # Cohen's h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
        h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
        print(f"  Cohen's h (accuracy): {h:.3f}")
        if abs(h) < 0.2:
            print(f"    Interpretation: Small effect")
        elif abs(h) < 0.5:
            print(f"    Interpretation: Small-to-medium effect")
        elif abs(h) < 0.8:
            print(f"    Interpretation: Medium effect")
        else:
            print(f"    Interpretation: Large effect")

    # Cohen's d for spans examined
    if at_spans and otel_spans:
        pooled_std = math.sqrt(
            (statistics.variance(at_spans) * (len(at_spans) - 1)
             + statistics.variance(otel_spans) * (len(otel_spans) - 1))
            / (len(at_spans) + len(otel_spans) - 2)
        ) if len(at_spans) > 1 and len(otel_spans) > 1 else 1.0
        d = (otel_spans_mean - at_spans_mean) / pooled_std if pooled_std > 0 else 0
        print(f"  Cohen's d (spans examined): {d:.3f}")
        if abs(d) < 0.2:
            print(f"    Interpretation: Small effect")
        elif abs(d) < 0.5:
            print(f"    Interpretation: Small-to-medium effect")
        elif abs(d) < 0.8:
            print(f"    Interpretation: Medium effect")
        else:
            print(f"    Interpretation: Large effect")

    # ---- Summary ----
    print(f"\n{'=' * 72}")
    print("SUMMARY")
    print(f"{'=' * 72}")
    print(f"  Conditions: AgentTelemetry (9 span kinds) vs Vanilla OTel (INTERNAL)")
    print(f"  Personas: {len(PERSONAS)}")
    print(f"  Traces: {len(selected)} (failed SWE-bench instances)")
    print(f"  Total LLM calls: {call_num}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"")
    print(f"  Diagnostic accuracy:")
    print(f"    AgentTelemetry: {at_acc:.1f}%  (CI: [{at_ci[0]*100:.1f}%, {at_ci[1]*100:.1f}%])")
    print(f"    Vanilla OTel:   {otel_acc:.1f}%  (CI: [{otel_ci[0]*100:.1f}%, {otel_ci[1]*100:.1f}%])")
    print(f"")
    print(f"  Spans examined (mean):")
    print(f"    AgentTelemetry: {at_spans_mean:.1f}")
    print(f"    Vanilla OTel:   {otel_spans_mean:.1f}")
    print(f"    Reduction: {reduction:.1f}%")

    # ---- Save results ----
    output = {
        "metadata": {
            "n_personas": len(PERSONAS),
            "n_traces": len(selected),
            "n_conditions": 2,
            "n_total_calls": call_num,
            "model": MODEL,
            "total_cost": total_cost,
            "traces_used": [r["instance_id"] for r in selected],
            "repos_used": list(set(r["repo"] for r in selected)),
        },
        "aggregate": {
            "agenttelemetry": {
                "accuracy": at_acc,
                "accuracy_ci_95": [at_ci[0] * 100, at_ci[1] * 100],
                "correct": at_correct,
                "total": at_total,
                "spans_examined_mean": at_spans_mean,
                "spans_examined_ci_95": list(at_spans_ci),
            },
            "vanilla_otel": {
                "accuracy": otel_acc,
                "accuracy_ci_95": [otel_ci[0] * 100, otel_ci[1] * 100],
                "correct": otel_correct,
                "total": otel_total,
                "spans_examined_mean": otel_spans_mean,
                "spans_examined_ci_95": list(otel_spans_ci),
            },
            "accuracy_improvement_pp": at_acc - otel_acc,
            "spans_reduction_pct": reduction,
        },
        "per_persona": persona_results,
        "diagnoses": [
            {
                "persona_id": d["persona_id"],
                "persona_label": d["persona_label"],
                "condition": d["condition"],
                "instance_id": d["instance_id"],
                "repo": d.get("repo", ""),
                "correct": d.get("correct", False),
                "spans_examined": d.get("spans_examined", -1),
                "confidence": d.get("confidence", ""),
                "root_cause": d.get("root_cause", ""),
                "reasoning": d.get("reasoning", ""),
                "cost": d.get("cost", 0),
            }
            for d in all_diagnoses
        ],
    }

    outfile = OUTPUT_DIR / "simulated_user_study.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {outfile}")

    # Also save the full table as TSV for easy import
    tsvfile = OUTPUT_DIR / "results_table.tsv"
    with open(tsvfile, "w") as f:
        f.write("Persona\tCondition\tInstance\tCorrect\tSpans_Examined\tConfidence\tRoot_Cause\n")
        for d in all_diagnoses:
            f.write(
                f"{d['persona_label']}\t{d.get('condition_label','')}\t"
                f"{d['instance_id']}\t{d.get('correct', False)}\t"
                f"{d.get('spans_examined', -1)}\t{d.get('confidence', '')}\t"
                f"{d.get('root_cause', '')}\n"
            )
    print(f"  TSV table saved to {tsvfile}")

    print(f"\n{'=' * 72}")
    print("SIMULATED USER STUDY COMPLETE")
    print(f"{'=' * 72}")

    return output


if __name__ == "__main__":
    main()
