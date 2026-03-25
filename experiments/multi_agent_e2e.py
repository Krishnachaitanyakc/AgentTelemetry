"""Multi-agent E2E test: 3-agent crew with all 9 span kinds.

Simulates a CrewAI-style planner/researcher/writer crew using
the Custom adapter and real OpenAI API calls.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from openai import OpenAI

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
from agenttelemetry.analysis import AnomalyDetector, CostAggregator, DecisionAttributor

RESULTS_DIR = PROJECT_ROOT / "results" / "multi_agent_e2e"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Multi-Agent E2E Test: 3-Agent Crew (All 9 Span Kinds)")
    print("=" * 60)

    provider = AgentTelemetryProvider(
        service_name="multi_agent_e2e",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(str(RESULTS_DIR / "traces.jsonl"))
    provider.setup(set_global=True)
    tracer = provider.get_tracer("multi_agent")

    client = OpenAI()
    task = "Research and write a brief summary about the impact of AI on healthcare."

    # === AGENT 1: Planner ===
    print("\n[Agent 1: Planner]")
    with start_agent_span(name="planner_agent", kind=AgentSpanKind.AGENT, tracer=tracer,
                          attributes={AGENT_NAME: "planner", AGENT_FRAMEWORK: "crew_sim", AGENT_TASK: task}):

        # PLANNING span
        with start_agent_span(name="create_research_plan", kind=AgentSpanKind.PLANNING, tracer=tracer,
                              attributes={PLANNING_STRATEGY: "decompose_into_subtasks", PLANNING_STEP_COUNT: 3}):
            pass

        # MEMORY read
        with start_agent_span(name="read_context", kind=AgentSpanKind.MEMORY, tracer=tracer,
                              attributes={MEMORY_OPERATION: "read", MEMORY_KEY: "task_context"}):
            pass

        # LLM call to create plan
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a research planner. Create a 3-step plan."},
                {"role": "user", "content": f"Plan research on: {task}"},
            ],
            max_tokens=200,
        )
        usage = response.usage
        with start_agent_span(name="plan_llm_call", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                              attributes={
                                  LLM_MODEL: "gpt-4o-mini", LLM_PROVIDER: "openai",
                                  LLM_INPUT_TOKENS: usage.prompt_tokens,
                                  LLM_OUTPUT_TOKENS: usage.completion_tokens,
                                  LLM_COST: estimate_cost("gpt-4o-mini", usage.prompt_tokens, usage.completion_tokens),
                              }):
            pass

        plan = response.choices[0].message.content
        print(f"  Plan: {plan[:80]}...")

        # DELEGATION to researcher
        with start_agent_span(name="delegate_to_researcher", kind=AgentSpanKind.DELEGATION, tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "planner", DELEGATION_TARGET_AGENT: "researcher"}):
            pass

    # === AGENT 2: Researcher ===
    print("[Agent 2: Researcher]")
    with start_agent_span(name="researcher_agent", kind=AgentSpanKind.AGENT, tracer=tracer,
                          attributes={AGENT_NAME: "researcher", AGENT_FRAMEWORK: "crew_sim"}):

        # RETRIEVAL span
        with start_agent_span(name="search_papers", kind=AgentSpanKind.RETRIEVAL, tracer=tracer,
                              attributes={RETRIEVAL_QUERY: "AI healthcare impact", RETRIEVAL_SOURCE: "knowledge_base",
                                         RETRIEVAL_DOC_COUNT: 5}):
            pass

        # TOOL_CALL span
        with start_agent_span(name="summarize_tool", kind=AgentSpanKind.TOOL_CALL, tracer=tracer,
                              attributes={TOOL_NAME: "summarizer", TOOL_INPUT: "AI healthcare papers",
                                         TOOL_OUTPUT: "Key findings: ...", TOOL_STATUS: "OK"}):
            pass

        # REASONING span
        with start_agent_span(name="synthesize_findings", kind=AgentSpanKind.REASONING, tracer=tracer,
                              attributes={REASONING_CHAIN: "Analyzing retrieved papers on AI in healthcare diagnostics, drug discovery, and patient care"}):
            pass

        # LLM call for research synthesis
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a researcher. Synthesize findings about AI in healthcare."},
                {"role": "user", "content": "Summarize the key impacts of AI on healthcare in 3 bullet points."},
            ],
            max_tokens=200,
        )
        usage = response.usage
        with start_agent_span(name="research_llm_call", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                              attributes={
                                  LLM_MODEL: "gpt-4o-mini", LLM_PROVIDER: "openai",
                                  LLM_INPUT_TOKENS: usage.prompt_tokens,
                                  LLM_OUTPUT_TOKENS: usage.completion_tokens,
                                  LLM_COST: estimate_cost("gpt-4o-mini", usage.prompt_tokens, usage.completion_tokens),
                              }):
            pass

        research = response.choices[0].message.content
        print(f"  Research: {research[:80]}...")

        # DELEGATION to writer
        with start_agent_span(name="delegate_to_writer", kind=AgentSpanKind.DELEGATION, tracer=tracer,
                              attributes={DELEGATION_SOURCE_AGENT: "researcher", DELEGATION_TARGET_AGENT: "writer"}):
            pass

    # === AGENT 3: Writer ===
    print("[Agent 3: Writer]")
    with start_agent_span(name="writer_agent", kind=AgentSpanKind.AGENT, tracer=tracer,
                          attributes={AGENT_NAME: "writer", AGENT_FRAMEWORK: "crew_sim"}):

        # MEMORY read
        with start_agent_span(name="load_research", kind=AgentSpanKind.MEMORY, tracer=tracer,
                              attributes={MEMORY_OPERATION: "read", MEMORY_KEY: "research_findings"}):
            pass

        # LLM call for writing
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technical writer. Write a concise summary."},
                {"role": "user", "content": f"Write a 2-sentence summary based on: {research[:500]}"},
            ],
            max_tokens=150,
        )
        usage = response.usage
        with start_agent_span(name="write_llm_call", kind=AgentSpanKind.LLM_CALL, tracer=tracer,
                              attributes={
                                  LLM_MODEL: "gpt-4o-mini", LLM_PROVIDER: "openai",
                                  LLM_INPUT_TOKENS: usage.prompt_tokens,
                                  LLM_OUTPUT_TOKENS: usage.completion_tokens,
                                  LLM_COST: estimate_cost("gpt-4o-mini", usage.prompt_tokens, usage.completion_tokens),
                              }):
            pass

        output = response.choices[0].message.content
        print(f"  Output: {output[:80]}...")

        # GUARD_RAIL span
        with start_agent_span(name="content_safety_check", kind=AgentSpanKind.GUARD_RAIL, tracer=tracer,
                              attributes={GUARDRAIL_NAME: "content_policy", GUARDRAIL_RESULT: "PASS"}):
            pass

        # MEMORY write
        with start_agent_span(name="save_output", kind=AgentSpanKind.MEMORY, tracer=tracer,
                              attributes={MEMORY_OPERATION: "write", MEMORY_KEY: "final_output"}):
            pass

    provider.shutdown()

    # === Analysis ===
    spans = json_exporter.get_exported_spans()
    print(f"\n{len(spans)} spans exported")

    kind_counts = {}
    for s in spans:
        kind = s.get("agent_span_kind", "UNKNOWN") or "UNKNOWN"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    print("Span kinds:")
    for k, v in sorted(kind_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    cost_report = CostAggregator().analyze(spans)
    anomalies = AnomalyDetector(max_retries=5, cost_threshold=0.50).detect(spans)
    decisions = DecisionAttributor().analyze(spans)

    print(f"\nCost: ${cost_report.total_cost:.6f}")
    print(f"Anomalies: {len(anomalies)}")
    print(f"Decisions traced: {len(decisions)}")

    # Validate ALL 9 span kinds present
    all_9 = {"AGENT", "LLM_CALL", "TOOL_CALL", "PLANNING", "REASONING",
             "RETRIEVAL", "GUARD_RAIL", "DELEGATION", "MEMORY"}

    checks = {}
    for kind in sorted(all_9):
        present = kind_counts.get(kind, 0) > 0
        checks[kind] = present

    checks["Cost > $0"] = cost_report.total_cost > 0
    checks["No false anomalies"] = len(anomalies) == 0

    print(f"\nValidation:")
    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {check}")

    summary = {
        "spans": len(spans),
        "kinds": kind_counts,
        "all_9_present": all(kind_counts.get(k, 0) > 0 for k in all_9),
        "cost": cost_report.total_cost,
        "anomalies": len(anomalies),
        "decisions": len(decisions),
        "all_pass": all_pass,
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print("ALL 9 SPAN KINDS VALIDATED" if all_pass else "SOME CHECKS FAILED")
    print(f"{'=' * 60}")
    return all_pass


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
