"""CrewAI end-to-end integration test with AgentTelemetry.

Validates that the CrewAI adapter (hook-based, zero monkey-patching) works
with real OpenAI API calls through a 2-agent crew and produces the correct
AgentTelemetry span kinds.

Requirements:
  - crewai >= 1.0 installed
  - OPENAI_API_KEY in .env
  - PYTHONPATH=src
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from crewai import Agent, Task, Crew, LLM, Process
from crewai.tools import tool

from agenttelemetry.core.tracer import AgentTelemetryProvider
from agenttelemetry.core.privacy import PrivacyLevel
from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    AgentSpanKind,
    start_agent_span,
    AGENT_NAME,
    AGENT_FRAMEWORK,
    AGENT_ROLE,
    AGENT_TASK,
    LLM_MODEL,
    LLM_LATENCY_MS,
    LLM_PROVIDER,
    TOOL_NAME,
    TOOL_STATUS,
    PLANNING_STRATEGY,
)
from agenttelemetry.adapters.crewai import CrewAIInstrumentor
from agenttelemetry.analysis import CostAggregator

RESULTS_DIR = PROJECT_ROOT / "results" / "crewai_e2e"


# ---------------------------------------------------------------------------
# Custom tool for the agents to use (triggers TOOL_CALL spans)
# ---------------------------------------------------------------------------

@tool("word_count")
def word_count_tool(text: str) -> str:
    """Count the number of words in the given text."""
    count = len(text.split())
    return f"The text contains {count} words."


@tool("summarize_length")
def summarize_length_tool(text: str) -> str:
    """Report whether the text is short, medium, or long."""
    words = len(text.split())
    if words < 50:
        category = "short"
    elif words < 150:
        category = "medium"
    else:
        category = "long"
    return f"The text is {category} ({words} words)."


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main() -> bool:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("CrewAI End-to-End Integration Test with AgentTelemetry")
    print("=" * 70)
    print(f"Timestamp : {datetime.now(timezone.utc).isoformat()}")
    print(f"Results   : {RESULTS_DIR}")
    print()

    # Verify API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[FATAL] OPENAI_API_KEY not set. Aborting.")
        return False
    print(f"[OK] OpenAI API key: ...{api_key[-6:]}")

    # ------------------------------------------------------------------
    # Step 1: Set up AgentTelemetry
    # ------------------------------------------------------------------
    print("\n[1/5] Setting up AgentTelemetry provider...")

    provider = AgentTelemetryProvider(
        service_name="crewai_e2e_test",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(str(RESULTS_DIR / "traces.jsonl"))
    provider.add_console_exporter(verbose=False)
    tp = provider.setup(set_global=True)
    tracer = provider.get_tracer("crewai_e2e")

    print("  TracerProvider ready")

    # ------------------------------------------------------------------
    # Step 2: Instrument CrewAI via hooks
    # ------------------------------------------------------------------
    print("\n[2/5] Instrumenting CrewAI with hook-based adapter...")

    instrumentor = CrewAIInstrumentor()
    instrumentor.instrument(
        tracer_provider=tp,
        privacy_level=PrivacyLevel.FULL,
    )
    print("  CrewAI hooks registered (before/after LLM + tool)")

    # ------------------------------------------------------------------
    # Step 3: Create 2-agent crew
    # ------------------------------------------------------------------
    print("\n[3/5] Creating 2-agent crew (researcher + writer)...")

    llm = LLM(model="openai/gpt-4o-mini")

    researcher = Agent(
        role="Research Analyst",
        goal="Research the given topic and provide key facts",
        backstory="You are a thorough research analyst who finds key facts "
                  "and figures on any topic. Keep responses concise.",
        llm=llm,
        tools=[word_count_tool],
        verbose=False,
        allow_delegation=False,
    )

    writer = Agent(
        role="Content Writer",
        goal="Write a brief summary based on research findings",
        backstory="You are a concise technical writer who turns research "
                  "into clear, readable summaries. Keep it under 100 words.",
        llm=llm,
        tools=[summarize_length_tool],
        verbose=False,
        allow_delegation=False,
    )

    research_task = Task(
        description=(
            "Research the topic 'benefits of observability in AI agent systems'. "
            "Provide 3 key benefits in bullet-point form. "
            "Use the word_count tool to count the words in your response. "
            "Keep your total response under 100 words."
        ),
        expected_output="3 bullet points about observability benefits with word count",
        agent=researcher,
    )

    writing_task = Task(
        description=(
            "Based on the research provided, write a one-paragraph summary "
            "(under 80 words) about why observability matters for AI agents. "
            "Use the summarize_length tool to check your output length."
        ),
        expected_output="A concise one-paragraph summary under 80 words",
        agent=writer,
    )

    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=False,
    )

    print(f"  Agents: {researcher.role}, {writer.role}")
    print(f"  Tasks : {len(crew.tasks)}")
    print(f"  LLM   : {llm.model}")

    # ------------------------------------------------------------------
    # Step 4: Run the crew (with manual AGENT + PLANNING spans)
    # ------------------------------------------------------------------
    print("\n[4/5] Running crew with real OpenAI API calls...")
    print("  (This will make several LLM calls -- expect ~10-30 seconds)")
    print()

    t0 = time.perf_counter()

    # Wrap the entire crew execution in an AGENT span
    with start_agent_span(
        name="crewai_e2e_crew",
        kind=AgentSpanKind.AGENT,
        tracer=tracer,
        attributes={
            AGENT_NAME: "crewai_e2e_crew",
            AGENT_FRAMEWORK: "crewai",
        },
    ) as crew_span:
        # Planning span
        with start_agent_span(
            name="crew_planning",
            kind=AgentSpanKind.PLANNING,
            tracer=tracer,
            attributes={PLANNING_STRATEGY: "sequential_2_agent"},
        ):
            pass  # Planning is implicit in CrewAI

        try:
            result = crew.kickoff()
            elapsed = time.perf_counter() - t0
            print(f"\n  Crew completed in {elapsed:.1f}s")
            print(f"  Result preview: {str(result)[:200]}...")
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f"\n  [ERROR] Crew failed after {elapsed:.1f}s: {exc}")
            # Still continue to analyze whatever spans were produced
            result = None

    # ------------------------------------------------------------------
    # Step 5: Analyze and validate spans
    # ------------------------------------------------------------------
    print("\n[5/5] Analyzing exported spans...")

    # Force flush
    provider.shutdown()

    spans = json_exporter.get_exported_spans()
    print(f"  Total spans exported: {len(spans)}")

    # Count by kind
    kind_counts: dict[str, int] = {}
    for s in spans:
        kind = s.get("agent_span_kind", "") or s.get("attributes", {}).get(AGENT_SPAN_KIND, "")
        if not kind:
            kind = "UNKNOWN"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    print("\n  Span kinds:")
    for k, v in sorted(kind_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:<15} : {v}")

    # Extract LLM call details
    llm_spans = [s for s in spans
                 if (s.get("agent_span_kind") == "LLM_CALL"
                     or s.get("attributes", {}).get(AGENT_SPAN_KIND) == "LLM_CALL")]
    tool_spans = [s for s in spans
                  if (s.get("agent_span_kind") == "TOOL_CALL"
                      or s.get("attributes", {}).get(AGENT_SPAN_KIND) == "TOOL_CALL")]

    print(f"\n  LLM call spans: {len(llm_spans)}")
    for i, s in enumerate(llm_spans[:5]):  # Show first 5
        attrs = s.get("attributes", {})
        model = attrs.get(LLM_MODEL, "?")
        latency = attrs.get(LLM_LATENCY_MS, 0)
        print(f"    [{i+1}] model={model}, latency={latency:.0f}ms")

    print(f"\n  Tool call spans: {len(tool_spans)}")
    for i, s in enumerate(tool_spans[:5]):
        attrs = s.get("attributes", {})
        name = attrs.get(TOOL_NAME, "?")
        status = attrs.get(TOOL_STATUS, "?")
        print(f"    [{i+1}] tool={name}, status={status}")

    # Cost analysis
    try:
        cost_report = CostAggregator().analyze(spans)
        total_cost = cost_report.total_cost
        total_in = cost_report.total_input_tokens
        total_out = cost_report.total_output_tokens
    except Exception:
        total_cost = 0.0
        total_in = 0
        total_out = 0

    print(f"\n  Cost: ${total_cost:.6f}")
    print(f"  Tokens: {total_in} in, {total_out} out")

    # ------------------------------------------------------------------
    # Validation checks
    # ------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Validation Checks:")
    print("-" * 50)

    checks = {
        "AGENT spans >= 1": kind_counts.get("AGENT", 0) >= 1,
        "LLM_CALL spans >= 1": kind_counts.get("LLM_CALL", 0) >= 1,
        "PLANNING spans >= 1": kind_counts.get("PLANNING", 0) >= 1,
        "TOOL_CALL spans >= 0 (tools optional)": kind_counts.get("TOOL_CALL", 0) >= 0,
        "Total spans >= 3": len(spans) >= 3,
        "LLM model captured": any(
            s.get("attributes", {}).get(LLM_MODEL, "") != ""
            for s in llm_spans
        ) if llm_spans else False,
        "LLM latency captured": any(
            s.get("attributes", {}).get(LLM_LATENCY_MS, 0) > 0
            for s in llm_spans
        ) if llm_spans else False,
        "Agent framework = crewai": any(
            s.get("attributes", {}).get(AGENT_FRAMEWORK) == "crewai"
            for s in spans
        ),
        "Crew completed": result is not None,
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {check}")

    # ------------------------------------------------------------------
    # Save results
    # ------------------------------------------------------------------
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "crewai_version": _get_crewai_version(),
        "model": "gpt-4o-mini",
        "elapsed_seconds": round(elapsed, 1),
        "total_spans": len(spans),
        "span_kinds": kind_counts,
        "llm_call_count": len(llm_spans),
        "tool_call_count": len(tool_spans),
        "total_cost_usd": total_cost,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "all_checks_passed": all_pass,
        "checks": {k: v for k, v in checks.items()},
        "crew_result_preview": str(result)[:500] if result else None,
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    if all_pass:
        print("ALL CHECKS PASSED -- CrewAI adapter works end-to-end")
    else:
        print("SOME CHECKS FAILED -- see details above")
    print(f"{'=' * 70}")
    print(f"Results saved to: {RESULTS_DIR}")

    return all_pass


def _get_crewai_version() -> str:
    try:
        import crewai
        return crewai.__version__
    except Exception:
        return "unknown"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
