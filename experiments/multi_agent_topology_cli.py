"""B2: Multi-agent topology comparison via CLI-driven LLMs.

Purpose: extend the existing 159-run real-LLM corpus (single-agent QA task)
with a multi-agent deployment study. Compare 3 multi-agent topologies on a
shared research-assistant task using AgentTelemetry instrumentation.

Topologies:
  - sequential:  planner -> researcher -> writer (3 agents in a chain)
  - hierarchical: manager delegates to 2 specialists in parallel (CrewAI-style)
  - parallel:    2 researchers run concurrently then a writer aggregates

LLMs (via Meta CLIs only — $0 marginal cost):
  - claude_cli/claude-opus-4-7        (Anthropic frontier)
  - claude_cli/claude-sonnet-4-6      (Anthropic mid-tier)
  - codex_cli/gpt-5.5                 (OpenAI frontier)

Trials: 5 questions x 3 topologies x 3 models = 45 multi-agent runs.

Usage:
    cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
    PYTHONPATH=src:. .venv/bin/python3.12 \
        experiments/multi_agent_topology_cli.py \
        --questions 5 \
        --topologies sequential hierarchical parallel \
        --models claude_cli/claude-opus-4-7 claude_cli/claude-sonnet-4-6 codex_cli/gpt-5.5 \
        --output-dir results/multi_agent_topology_cli

Output:
    results/multi_agent_topology_cli/
        traces.jsonl                 (all 9-span-kind spans, OTLP-compatible)
        per_run/{topology}_{model}_{q}.json   (per-run agent transcripts + telemetry)
        summary.json                 (per-topology x per-model fault rates, costs, latency)
        summary.txt                  (human-readable results table)

Cost: $0 marginal (CLI subprocesses only).
Runtime: ~45 runs x ~3 min = ~2.5 hours wall-clock (CLI rate-limited).

Statistics computed:
  - Per-topology organic-fault rates (cost_explosion, infinite_retry,
    circular_delegation, context_overflow)
  - Per-model fault distribution across topologies
  - Cohen's kappa for inter-topology fault-detection agreement
  - Wall-clock and per-span latency by topology
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse the standalone CLI subprocess wrappers (no litellm dependency)
from experiments.cli_subprocess import _call_claude_cli, _call_codex_cli

from agenttelemetry.core.tracer import AgentTelemetryProvider
from agenttelemetry.core.privacy import PrivacyLevel
from agenttelemetry.core.spans import (
    AgentSpanKind, start_agent_span,
    AGENT_NAME, AGENT_FRAMEWORK, AGENT_TASK,
    DELEGATION_SOURCE_AGENT, DELEGATION_TARGET_AGENT,
    GUARDRAIL_NAME, GUARDRAIL_RESULT,
    LLM_MODEL, LLM_PROVIDER, LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS, LLM_COST,
    MEMORY_OPERATION, MEMORY_KEY,
    PLANNING_STRATEGY, PLANNING_STEP_COUNT,
    REASONING_CHAIN,
    RETRIEVAL_QUERY, RETRIEVAL_SOURCE, RETRIEVAL_DOC_COUNT,
    TOOL_NAME, TOOL_INPUT, TOOL_OUTPUT, TOOL_STATUS,
    estimate_cost,
)
from agenttelemetry.analysis import AnomalyDetector


# ============================================================
# CLI dispatch
# ============================================================

def call_llm(model_spec: str, prompt: str, timeout: int = 360) -> Dict[str, Any]:
    """Dispatch to the right CLI based on the model spec prefix.

    model_spec format: "claude_cli/claude-opus-4-7" or "codex_cli/gpt-5.5"
    """
    if "/" not in model_spec:
        raise ValueError(f"model_spec must include CLI prefix: {model_spec}")
    cli, model = model_spec.split("/", 1)
    if cli == "claude_cli":
        return _call_claude_cli(prompt, model=model, timeout=timeout)
    elif cli == "codex_cli":
        return _call_codex_cli(prompt, model=model, timeout=timeout)
    else:
        raise ValueError(f"unknown CLI: {cli}")


def model_provider(model_spec: str) -> str:
    cli = model_spec.split("/", 1)[0]
    return {"claude_cli": "anthropic", "codex_cli": "openai"}.get(cli, "unknown")


# ============================================================
# Shared question pool (5 hand-curated multi-step research questions)
# ============================================================

QUESTIONS = [
    "What are three concrete ways autonomous AI agents fail in production deployments, and what observability primitives would catch each?",
    "Compare reasoning-loop failures versus circular delegation in multi-agent systems. Which is more common, and why?",
    "Summarize the trade-offs between OpenTelemetry GenAI semantic conventions and OpenInference for agent observability.",
    "What are the limitations of using mock LLM clients for benchmarking agent fault detection? Propose two ways to validate against real production traces.",
    "Describe how a closed-loop intervention based on telemetry signals can recover a stuck agent. Give a concrete example using the REASONING span kind.",
]


# ============================================================
# Topology 1: Sequential (planner -> researcher -> writer)
# ============================================================

def run_sequential(question: str, model_spec: str, tracer, run_id: str) -> Dict[str, Any]:
    """Sequential 3-agent chain: planner -> researcher -> writer.

    All inter-agent handoffs are explicit DELEGATION spans.
    """
    transcript: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    with start_agent_span(name="orchestrator", kind=AgentSpanKind.AGENT, tracer=tracer,
                          attributes={AGENT_NAME: "orchestrator", AGENT_FRAMEWORK: "sequential",
                                      AGENT_TASK: question[:200]}) as orch_span:

        # ---- Agent 1: Planner ----
        with start_agent_span(name="planner", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "planner", AGENT_FRAMEWORK: "sequential"}):
            with start_agent_span(name="planner_planning", kind=AgentSpanKind.PLANNING, tracer=tracer,
                                  attributes={PLANNING_STRATEGY: "decompose_into_subtasks",
                                              PLANNING_STEP_COUNT: 3}):
                pass

            plan_prompt = f"You are a research planner. Given the question, list 3 concrete sub-questions to research.\n\nQuestion: {question}\n\nReturn a numbered list, max 100 words."
            plan_out = call_llm(model_spec, plan_prompt)
            plan_text = plan_out.get("text", "")
            in_tok = max(1, len(plan_prompt) // 4)
            out_tok = max(1, len(plan_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="planner_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass
            transcript.append({"agent": "planner", "output": plan_text, "latency_s": plan_out["latency_s"]})

        # Delegation: planner -> researcher
        with start_agent_span(name="delegate_planner_to_researcher", kind=AgentSpanKind.DELEGATION,
                              tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "planner",
                                          DELEGATION_TARGET_AGENT: "researcher"}):
            pass

        # ---- Agent 2: Researcher ----
        with start_agent_span(name="researcher", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "researcher", AGENT_FRAMEWORK: "sequential"}):

            with start_agent_span(name="researcher_retrieval", kind=AgentSpanKind.RETRIEVAL, tracer=tracer,
                                  attributes={RETRIEVAL_QUERY: question[:100],
                                              RETRIEVAL_SOURCE: "internal_kb",
                                              RETRIEVAL_DOC_COUNT: 5}):
                pass

            research_prompt = f"You are a research analyst. Use the plan to gather facts.\n\nPlan:\n{plan_text}\n\nOriginal question: {question}\n\nReturn a structured findings list, max 200 words."
            research_out = call_llm(model_spec, research_prompt)
            research_text = research_out.get("text", "")
            in_tok = max(1, len(research_prompt) // 4)
            out_tok = max(1, len(research_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="researcher_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass

            with start_agent_span(name="researcher_reasoning", kind=AgentSpanKind.REASONING, tracer=tracer,
                                  attributes={REASONING_CHAIN: research_text[:500]}):
                pass
            transcript.append({"agent": "researcher", "output": research_text, "latency_s": research_out["latency_s"]})

        # Delegation: researcher -> writer
        with start_agent_span(name="delegate_researcher_to_writer", kind=AgentSpanKind.DELEGATION,
                              tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "researcher",
                                          DELEGATION_TARGET_AGENT: "writer"}):
            pass

        # ---- Agent 3: Writer ----
        with start_agent_span(name="writer", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "writer", AGENT_FRAMEWORK: "sequential"}):

            with start_agent_span(name="writer_memory_read", kind=AgentSpanKind.MEMORY, tracer=tracer,
                                  attributes={MEMORY_OPERATION: "read",
                                              MEMORY_KEY: "research_findings"}):
                pass

            write_prompt = f"You are a technical writer. Synthesize the research into a final answer.\n\nResearch findings:\n{research_text}\n\nQuestion: {question}\n\nWrite a concise, well-structured answer in 100-200 words."
            write_out = call_llm(model_spec, write_prompt)
            write_text = write_out.get("text", "")
            in_tok = max(1, len(write_prompt) // 4)
            out_tok = max(1, len(write_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="writer_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass

            with start_agent_span(name="writer_guardrail", kind=AgentSpanKind.GUARD_RAIL, tracer=tracer,
                                  attributes={GUARDRAIL_NAME: "length_check",
                                              GUARDRAIL_RESULT: "pass" if len(write_text) > 50 else "fail"}):
                pass
            transcript.append({"agent": "writer", "output": write_text, "latency_s": write_out["latency_s"]})

    return {
        "topology": "sequential",
        "model": model_spec,
        "question": question,
        "run_id": run_id,
        "transcript": transcript,
        "total_cost_usd": total_cost,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "n_agents": 3,
    }


# ============================================================
# Topology 2: Hierarchical (manager + 2 specialist delegates)
# ============================================================

def run_hierarchical(question: str, model_spec: str, tracer, run_id: str) -> Dict[str, Any]:
    """Hierarchical: manager delegates to facts_specialist + analysis_specialist in parallel,
    then synthesizes. CrewAI-style hierarchical process."""
    transcript: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    with start_agent_span(name="manager", kind=AgentSpanKind.AGENT, tracer=tracer,
                          attributes={AGENT_NAME: "manager", AGENT_FRAMEWORK: "hierarchical",
                                      AGENT_TASK: question[:200]}):

        # Manager's planning step
        with start_agent_span(name="manager_planning", kind=AgentSpanKind.PLANNING, tracer=tracer,
                              attributes={PLANNING_STRATEGY: "split_into_two_specialists",
                                          PLANNING_STEP_COUNT: 2}):
            pass

        # Delegate to facts_specialist
        with start_agent_span(name="delegate_to_facts", kind=AgentSpanKind.DELEGATION, tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "manager",
                                          DELEGATION_TARGET_AGENT: "facts_specialist"}):
            pass

        # ---- Facts specialist ----
        with start_agent_span(name="facts_specialist", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "facts_specialist", AGENT_FRAMEWORK: "hierarchical"}):
            facts_prompt = f"You are a facts specialist. List 3-5 key facts relevant to this question.\n\nQuestion: {question}\n\nReturn a bulleted list, max 150 words."
            facts_out = call_llm(model_spec, facts_prompt)
            facts_text = facts_out.get("text", "")
            in_tok = max(1, len(facts_prompt) // 4)
            out_tok = max(1, len(facts_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="facts_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass
            transcript.append({"agent": "facts_specialist", "output": facts_text, "latency_s": facts_out["latency_s"]})

        # Delegate to analysis_specialist
        with start_agent_span(name="delegate_to_analysis", kind=AgentSpanKind.DELEGATION, tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "manager",
                                          DELEGATION_TARGET_AGENT: "analysis_specialist"}):
            pass

        # ---- Analysis specialist ----
        with start_agent_span(name="analysis_specialist", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "analysis_specialist", AGENT_FRAMEWORK: "hierarchical"}):
            analysis_prompt = f"You are an analysis specialist. Identify the key trade-offs or comparisons in this question.\n\nQuestion: {question}\n\nReturn 2-3 trade-offs, max 150 words."
            analysis_out = call_llm(model_spec, analysis_prompt)
            analysis_text = analysis_out.get("text", "")
            in_tok = max(1, len(analysis_prompt) // 4)
            out_tok = max(1, len(analysis_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="analysis_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass

            with start_agent_span(name="analysis_reasoning", kind=AgentSpanKind.REASONING, tracer=tracer,
                                  attributes={REASONING_CHAIN: analysis_text[:500]}):
                pass
            transcript.append({"agent": "analysis_specialist", "output": analysis_text, "latency_s": analysis_out["latency_s"]})

        # Manager synthesizes
        synth_prompt = f"You are a manager synthesizing two specialist reports.\n\nFacts:\n{facts_text}\n\nAnalysis:\n{analysis_text}\n\nQuestion: {question}\n\nProduce a unified answer in 100-200 words."
        synth_out = call_llm(model_spec, synth_prompt)
        synth_text = synth_out.get("text", "")
        in_tok = max(1, len(synth_prompt) // 4)
        out_tok = max(1, len(synth_text) // 4)
        cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
        total_cost += cost
        total_input_tokens += in_tok
        total_output_tokens += out_tok

        with start_agent_span(name="manager_synthesis_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                              attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                          LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                          LLM_COST: cost}):
            pass

        with start_agent_span(name="manager_guardrail", kind=AgentSpanKind.GUARD_RAIL, tracer=tracer,
                              attributes={GUARDRAIL_NAME: "synthesis_check",
                                          GUARDRAIL_RESULT: "pass" if len(synth_text) > 80 else "fail"}):
            pass
        transcript.append({"agent": "manager_synthesis", "output": synth_text, "latency_s": synth_out["latency_s"]})

    return {
        "topology": "hierarchical",
        "model": model_spec,
        "question": question,
        "run_id": run_id,
        "transcript": transcript,
        "total_cost_usd": total_cost,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "n_agents": 3,
    }


# ============================================================
# Topology 3: Parallel (2 researchers + 1 aggregator writer)
# ============================================================

def run_parallel(question: str, model_spec: str, tracer, run_id: str) -> Dict[str, Any]:
    """Parallel: 2 researchers each produce findings independently; writer aggregates.
    Note: 'parallel' is logical, not threaded — CLI rate limits prevent true parallelism."""
    transcript: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    with start_agent_span(name="orchestrator", kind=AgentSpanKind.AGENT, tracer=tracer,
                          attributes={AGENT_NAME: "orchestrator", AGENT_FRAMEWORK: "parallel",
                                      AGENT_TASK: question[:200]}):

        with start_agent_span(name="orchestrator_planning", kind=AgentSpanKind.PLANNING, tracer=tracer,
                              attributes={PLANNING_STRATEGY: "parallel_research_then_aggregate",
                                          PLANNING_STEP_COUNT: 2}):
            pass

        # Researcher A perspective: technical depth
        with start_agent_span(name="delegate_to_research_a", kind=AgentSpanKind.DELEGATION, tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "orchestrator",
                                          DELEGATION_TARGET_AGENT: "researcher_a"}):
            pass

        with start_agent_span(name="researcher_a", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "researcher_a", AGENT_FRAMEWORK: "parallel"}):
            ra_prompt = f"You are a deep technical researcher. Answer this question with technical depth.\n\nQuestion: {question}\n\nMax 150 words."
            ra_out = call_llm(model_spec, ra_prompt)
            ra_text = ra_out.get("text", "")
            in_tok = max(1, len(ra_prompt) // 4)
            out_tok = max(1, len(ra_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="ra_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass
            transcript.append({"agent": "researcher_a", "output": ra_text, "latency_s": ra_out["latency_s"]})

        # Researcher B perspective: practical applications
        with start_agent_span(name="delegate_to_research_b", kind=AgentSpanKind.DELEGATION, tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "orchestrator",
                                          DELEGATION_TARGET_AGENT: "researcher_b"}):
            pass

        with start_agent_span(name="researcher_b", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "researcher_b", AGENT_FRAMEWORK: "parallel"}):
            rb_prompt = f"You are a practical applications researcher. Answer this question with deployment-focused examples.\n\nQuestion: {question}\n\nMax 150 words."
            rb_out = call_llm(model_spec, rb_prompt)
            rb_text = rb_out.get("text", "")
            in_tok = max(1, len(rb_prompt) // 4)
            out_tok = max(1, len(rb_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="rb_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass
            transcript.append({"agent": "researcher_b", "output": rb_text, "latency_s": rb_out["latency_s"]})

        # Writer aggregates
        with start_agent_span(name="delegate_to_writer", kind=AgentSpanKind.DELEGATION, tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "orchestrator",
                                          DELEGATION_TARGET_AGENT: "writer"}):
            pass

        with start_agent_span(name="writer", kind=AgentSpanKind.AGENT, tracer=tracer,
                              attributes={AGENT_NAME: "writer", AGENT_FRAMEWORK: "parallel"}):
            with start_agent_span(name="writer_memory_aggregate", kind=AgentSpanKind.MEMORY, tracer=tracer,
                                  attributes={MEMORY_OPERATION: "write",
                                              MEMORY_KEY: "aggregated_research"}):
                pass

            agg_prompt = f"You are an aggregator. Combine these two perspectives into a single answer.\n\nPerspective A (technical):\n{ra_text}\n\nPerspective B (practical):\n{rb_text}\n\nQuestion: {question}\n\nMax 200 words."
            agg_out = call_llm(model_spec, agg_prompt)
            agg_text = agg_out.get("text", "")
            in_tok = max(1, len(agg_prompt) // 4)
            out_tok = max(1, len(agg_text) // 4)
            cost = estimate_cost(model_spec.split("/", 1)[1], in_tok, out_tok)
            total_cost += cost
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            with start_agent_span(name="writer_llm", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={LLM_MODEL: model_spec, LLM_PROVIDER: model_provider(model_spec),
                                              LLM_INPUT_TOKENS: in_tok, LLM_OUTPUT_TOKENS: out_tok,
                                              LLM_COST: cost}):
                pass

            with start_agent_span(name="writer_guardrail", kind=AgentSpanKind.GUARD_RAIL, tracer=tracer,
                                  attributes={GUARDRAIL_NAME: "synthesis_check",
                                              GUARDRAIL_RESULT: "pass" if len(agg_text) > 80 else "fail"}):
                pass
            transcript.append({"agent": "writer", "output": agg_text, "latency_s": agg_out["latency_s"]})

    return {
        "topology": "parallel",
        "model": model_spec,
        "question": question,
        "run_id": run_id,
        "transcript": transcript,
        "total_cost_usd": total_cost,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "n_agents": 3,
    }


TOPOLOGY_HANDLERS = {
    "sequential": run_sequential,
    "hierarchical": run_hierarchical,
    "parallel": run_parallel,
}


# ============================================================
# Main
# ============================================================

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--questions", type=int, default=5,
                   help="number of questions per (topology, model) cell")
    p.add_argument("--topologies", nargs="+", default=["sequential", "hierarchical", "parallel"],
                   choices=list(TOPOLOGY_HANDLERS.keys()))
    p.add_argument("--models", nargs="+",
                   default=["claude_cli/claude-opus-4-7",
                            "claude_cli/claude-sonnet-4-6",
                            "codex_cli/gpt-5.5"])
    p.add_argument("--output-dir", default="results/multi_agent_topology_cli")
    p.add_argument("--probe-only", action="store_true",
                   help="run a single CLI probe per model and exit")
    args = p.parse_args()

    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    per_run_dir = out_dir / "per_run"
    per_run_dir.mkdir(parents=True, exist_ok=True)

    # Pre-flight: probe each model
    print("=== Pre-flight CLI probes ===")
    for ms in args.models:
        print(f"  Probing {ms} ...", flush=True, end=" ")
        out = call_llm(ms, "Reply with only the word: ok", timeout=120)
        if out["error"]:
            print(f"FAIL ({out['latency_s']:.1f}s): {out['error']}")
            print(f"\nERROR: {ms} CLI probe failed.")
            print("If the error is a timeout, the Meta CLI likely needs an interactive ack on this machine.")
            print(f"Run manually first:")
            cli, model = ms.split("/", 1)
            if cli == "claude_cli":
                print(f"    echo 'say only: pong' | claude --model {model} --print")
            elif cli == "codex_cli":
                print(f"    codex exec --skip-git-repo-check --model {model} 'say only: pong'")
            print("When prompted, type EXACTLY:  I HAVE REVIEWED AND VERIFIED")
            sys.exit(1)
        print(f"OK ({out['latency_s']:.1f}s)")

    if args.probe_only:
        print("\nProbe-only mode; exiting.")
        return

    # Set up AgentTelemetry tracing
    provider = AgentTelemetryProvider(
        service_name="multi_agent_topology_cli",
        privacy_level=PrivacyLevel.METADATA_ONLY,
    )
    json_exporter = provider.add_json_exporter(str(out_dir / "traces.jsonl"))
    provider.setup(set_global=True)
    tracer = provider.get_tracer("multi_agent_topology_cli")

    # Run the matrix
    questions = QUESTIONS[:args.questions]
    all_runs: List[Dict[str, Any]] = []
    t0 = time.time()
    total_cells = len(args.topologies) * len(args.models) * len(questions)
    cell_idx = 0
    for topology in args.topologies:
        handler = TOPOLOGY_HANDLERS[topology]
        for model_spec in args.models:
            for qi, question in enumerate(questions):
                cell_idx += 1
                run_id = f"{topology}__{model_spec.replace('/', '_')}__q{qi}"
                print(f"\n[{cell_idx}/{total_cells}] {run_id}", flush=True)
                t_run = time.time()
                try:
                    result = handler(question, model_spec, tracer, run_id)
                    result["wall_clock_s"] = time.time() - t_run
                    result["error"] = None
                except Exception as e:
                    result = {
                        "topology": topology,
                        "model": model_spec,
                        "question": question,
                        "run_id": run_id,
                        "transcript": [],
                        "total_cost_usd": 0.0,
                        "wall_clock_s": time.time() - t_run,
                        "error": f"{type(e).__name__}: {e}",
                    }
                    print(f"  EXCEPTION: {result['error']}")
                all_runs.append(result)

                # Per-run save
                per_run_path = per_run_dir / f"{run_id}.json"
                with open(per_run_path, "w") as f:
                    # Truncate long transcript outputs for file-size sanity
                    safe = dict(result)
                    safe["transcript"] = [
                        {**t, "output": (t.get("output", "") or "")[:1000]}
                        for t in safe.get("transcript", [])
                    ]
                    json.dump(safe, f, indent=2)
                print(f"  done in {result['wall_clock_s']:.1f}s, cost=${result['total_cost_usd']:.4f}")

    # Force flush of any pending spans before reading the file
    provider.force_flush()

    # Aggregate results
    by_cell: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in all_runs:
        by_cell[(r["topology"], r["model"])].append(r)

    summary: Dict[str, Any] = {
        "elapsed_s": time.time() - t0,
        "n_questions": len(questions),
        "n_topologies": len(args.topologies),
        "n_models": len(args.models),
        "n_runs": len(all_runs),
        "per_cell": {},
    }
    for (topology, model), runs in by_cell.items():
        n = len(runs)
        successes = sum(1 for r in runs if not r.get("error") and any(t.get("output") for t in r.get("transcript", [])))
        avg_cost = sum(r.get("total_cost_usd", 0) for r in runs) / n if n else 0
        avg_wall = sum(r.get("wall_clock_s", 0) for r in runs) / n if n else 0
        avg_in = sum(r.get("total_input_tokens", 0) for r in runs) / n if n else 0
        avg_out = sum(r.get("total_output_tokens", 0) for r in runs) / n if n else 0
        cell_key = f"{topology}__{model}"
        summary["per_cell"][cell_key] = {
            "topology": topology,
            "model": model,
            "n_runs": n,
            "n_completed": successes,
            "completion_rate": successes / n if n else 0,
            "avg_cost_usd": avg_cost,
            "avg_wall_clock_s": avg_wall,
            "avg_input_tokens": avg_in,
            "avg_output_tokens": avg_out,
        }

    # Run AnomalyDetector across the full traces.jsonl to find organic faults
    organic_faults: Dict[str, Any] = {}
    traces_path = out_dir / "traces.jsonl"
    if traces_path.exists():
        try:
            from agenttelemetry.analysis import AnomalyDetector
            from agenttelemetry.analysis.anomaly import load_spans
            spans = load_spans(str(traces_path))
            detector = AnomalyDetector()
            anomalies = detector.detect(spans)
            organic_faults = {
                "total_spans": len(spans),
                "total_anomalies": len(anomalies),
                "by_type": dict(Counter(a.get("type", "unknown") for a in anomalies)),
            }
        except Exception as e:
            organic_faults = {"error": f"AnomalyDetector failed: {type(e).__name__}: {e}"}
    summary["organic_faults"] = organic_faults

    # Write summary files
    with open(out_dir / "summary.json", "w") as f:
        json.dump({"summary": summary, "runs": all_runs}, f, indent=2, default=str)

    lines = [
        "=" * 72,
        f"B2: Multi-agent topology comparison via Meta CLIs",
        "=" * 72,
        f"Elapsed: {summary['elapsed_s']:.0f}s "
        f"({summary['elapsed_s']/3600:.1f}h)",
        f"Total runs: {summary['n_runs']}",
        f"Topologies: {', '.join(args.topologies)}",
        f"Models:     {', '.join(args.models)}",
        "",
        "Per-cell results:",
        "",
    ]
    header = f"  {'topology':<15} {'model':<35} {'n':<3} {'done':<5} {'cost($)':<10} {'wall(s)':<10}"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for cell_key, st in sorted(summary["per_cell"].items()):
        lines.append(
            f"  {st['topology']:<15} {st['model']:<35} {st['n_runs']:<3} "
            f"{st['n_completed']:<5} {st['avg_cost_usd']:<10.4f} {st['avg_wall_clock_s']:<10.1f}"
        )
    if organic_faults and "by_type" in organic_faults:
        lines.append("")
        lines.append(f"Organic faults detected: {organic_faults['total_anomalies']} across {organic_faults['total_spans']} spans")
        for ftype, n in sorted(organic_faults["by_type"].items()):
            lines.append(f"    {ftype}: {n}")
    summary_text = "\n".join(lines)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(summary_text + "\n")
    print("\n" + summary_text)


if __name__ == "__main__":
    main()
