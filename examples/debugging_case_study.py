#!/usr/bin/env python3
"""Debugging Case Study: Fault Injection in a Multi-Agent Pipeline.

Demonstrates how AgentTelemetry helps diagnose three common fault scenarios
in a planner -> researcher -> writer multi-agent pipeline:

  Scenario 1: Hallucinated retrieval -- RAG returns irrelevant results that
               propagate to the writer's output.
  Scenario 2: Tool timeout -- A web_search tool times out, causing the agent
               to retry with degraded context.
  Scenario 3: Cost overrun -- A reasoning loop makes excessive LLM calls,
               accumulating cost beyond a $1.00 threshold.

Each scenario is fully simulated (no API keys or real LLM needed).
Run standalone:

    PYTHONPATH=src python examples/debugging_case_study.py
"""

from __future__ import annotations

import json
import os
import time
import random
from typing import Dict, List, Optional, Tuple

from agenttelemetry.core.trace import (
    AgentTracer,
    AgentSpanKind,
    SpanStatus,
    ATTR_AGENT_NAME,
    ATTR_AGENT_TASK,
    ATTR_AGENT_ROLE,
    ATTR_LLM_MODEL,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_COST_USD,
    ATTR_LLM_LATENCY_MS,
    ATTR_LLM_PROMPT,
    ATTR_LLM_COMPLETION,
    ATTR_TOOL_NAME,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    ATTR_TOOL_ERROR,
    ATTR_TOOL_LATENCY_MS,
    ATTR_INTERACTION_TYPE,
    ATTR_INTERACTION_SOURCE,
    ATTR_INTERACTION_TARGET,
    estimate_cost,
)
from agenttelemetry.core.context import AgentContext
from agenttelemetry.core.events import EventType
from agenttelemetry.core.metrics import AgentMetrics
from agenttelemetry.exporters.console import ConsoleExporter
from agenttelemetry.exporters.json_file import JSONFileExporter


# ============================================================================
# Utilities
# ============================================================================

SEPARATOR = "=" * 76
SUBSEP = "-" * 76

def banner(title: str) -> None:
    print()
    print(SEPARATOR)
    print(f"  {title}")
    print(SEPARATOR)
    print()


def sub_banner(title: str) -> None:
    print()
    print(SUBSEP)
    print(f"  {title}")
    print(SUBSEP)
    print()


def print_trace_tree(spans: list, indent: int = 0) -> None:
    """Pretty-print spans as an indented trace tree."""
    # Build parent -> children map
    root_spans = []
    children_map: Dict[str, list] = {}
    span_map: Dict[str, dict] = {}
    for s in spans:
        span_map[s["span_id"]] = s
        parent = s.get("parent_span_id")
        if parent and parent in span_map:
            children_map.setdefault(parent, []).append(s)
        else:
            # Either root or parent not in this set -- treat as root
            root_spans.append(s)

    def _print(span: dict, depth: int) -> None:
        prefix = "  " * depth + ("|- " if depth > 0 else "")
        status = span["status"].upper()
        kind = span["kind"]
        name = span["name"]
        dur = f'{span.get("duration_ms", 0):.1f}ms'
        attrs = span.get("attributes", {})

        status_marker = "[OK]   " if status == "OK" else f"[{status}]"
        if status in ("ERROR", "TIMEOUT"):
            status_marker = f"[{status}]"

        line = f"{prefix}{status_marker} {kind:<12} {name:<36} {dur:>10}"

        # Add context-specific info
        extras = []
        if attrs.get(ATTR_LLM_INPUT_TOKENS):
            extras.append(
                f"{attrs[ATTR_LLM_INPUT_TOKENS]}->{attrs.get(ATTR_LLM_OUTPUT_TOKENS, 0)} tok"
            )
        if attrs.get(ATTR_LLM_COST_USD):
            extras.append(f"${attrs[ATTR_LLM_COST_USD]:.6f}")
        if attrs.get("retrieval.relevance_score") is not None:
            extras.append(f"relevance={attrs['retrieval.relevance_score']:.2f}")
        if attrs.get(ATTR_TOOL_ERROR):
            extras.append(f"error={attrs[ATTR_TOOL_ERROR]}")
        if extras:
            line += "  " + " | ".join(extras)

        # Show events
        events = span.get("events", [])
        event_notes = []
        for ev in events:
            if ev["event_type"] in ("cost_threshold", "error", "warning"):
                event_notes.append(f"  EVENT: {ev['name']} ({ev['event_type']})")

        print(line)
        for note in event_notes:
            print("  " * depth + "  " + note)

        for child in children_map.get(span["span_id"], []):
            _print(child, depth + 1)

    for root in root_spans:
        _print(root, 0)


# ============================================================================
# Simulated Agent Components
# ============================================================================

def _sim_delay(lo: float = 0.01, hi: float = 0.05) -> None:
    """Simulate latency."""
    time.sleep(random.uniform(lo, hi))


# ============================================================================
# SCENARIO 1: Hallucinated Retrieval
# ============================================================================

def scenario_hallucinated_retrieval() -> List[dict]:
    """Researcher's RAG retrieval returns irrelevant results.

    The retrieval span has a low relevance score (0.12).
    The subsequent LLM_CALL uses this poor context and produces an
    incorrect summary.  The writer then propagates the error into
    the final output.

    Without structured telemetry, you would only see the final bad output.
    With AgentTelemetry, you can trace back to the RETRIEVAL span,
    see the low relevance score, and identify the root cause.
    """
    banner("SCENARIO 1: Hallucinated Retrieval")

    all_spans: List[dict] = []

    # -- Planner --
    planner = AgentTracer(agent_name="planner", framework="custom")

    with planner.start_task("Summarize quantum computing advances") as task:
        _sim_delay()

        with planner.start_planning("decompose_task") as plan:
            _sim_delay()
            with planner.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.05, 0.1)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 320)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 150)

        # Propagate context to researcher
        ctx = AgentContext.from_tracer(planner)

        # -- Researcher (with hallucinated retrieval) --
        researcher = AgentTracer(agent_name="researcher", framework="custom")

        with researcher.start_task("research: quantum computing") as rtask:
            rtask.trace_id = ctx.trace_id
            rtask.parent_span_id = ctx.parent_span_id

            # RETRIEVAL: returns irrelevant documents (low relevance)
            with researcher.start_retrieval("rag_vector_search") as ret:
                _sim_delay(0.02, 0.06)
                ret.set_attribute("retrieval.query", "quantum computing advances 2025")
                ret.set_attribute("retrieval.top_k", 5)
                ret.set_attribute("retrieval.relevance_score", 0.12)  # Very low!
                ret.set_attribute(
                    "retrieval.documents",
                    [
                        "Recipe for chocolate cake...",
                        "History of the Roman Empire...",
                        "Quantum: a brand of dishwasher detergent...",
                    ],
                )
                ret.add_event(
                    "low_relevance_warning",
                    EventType.WARNING,
                    relevance_score=0.12,
                    threshold=0.5,
                    message="Retrieved documents have relevance below threshold",
                )

            # LLM_CALL: uses irrelevant context, produces hallucinated summary
            with researcher.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.05, 0.15)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 1800)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 400)
                llm.set_attribute(
                    "llm.context_quality", "degraded"
                )

        # -- Writer (propagates the hallucination) --
        writer = AgentTracer(agent_name="writer", framework="custom")

        with writer.start_task("write: final summary") as wtask:
            wtask.trace_id = ctx.trace_id
            wtask.parent_span_id = rtask.span_id

            with writer.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.05, 0.15)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 900)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 500)
                llm.set_attribute(
                    "output.quality",
                    "contains hallucinated claims from irrelevant retrieval",
                )

    # Collect all spans
    all_spans = (
        [s.to_dict() for s in planner.get_spans()]
        + [s.to_dict() for s in researcher.get_spans()]
        + [s.to_dict() for s in writer.get_spans()]
    )

    sub_banner("Trace Output")
    print_trace_tree(all_spans)

    sub_banner("Diagnosis")
    print(
        "  ROOT CAUSE: The RETRIEVAL span 'rag_vector_search' shows a relevance\n"
        "  score of 0.12, far below the 0.5 threshold.  A WARNING event was\n"
        "  recorded on the span.  The subsequent LLM_CALL consumed these\n"
        "  irrelevant documents (context_quality=degraded), and the writer\n"
        "  propagated the hallucination into the final output.\n"
        "\n"
        "  WHAT TELEMETRY REVEALS:\n"
        "    - retrieval.relevance_score = 0.12 on the RETRIEVAL span\n"
        "    - WARNING event: 'low_relevance_warning'\n"
        "    - llm.context_quality = 'degraded' on the researcher's LLM_CALL\n"
        "    - output.quality shows hallucinated claims in the writer's LLM_CALL\n"
        "\n"
        "  WITHOUT AgentTelemetry: You would only see the final bad output and\n"
        "  have no visibility into which pipeline stage introduced the error.\n"
        "  Framework-default logging does not capture relevance scores or\n"
        "  link retrieval quality to downstream LLM outputs across agent\n"
        "  boundaries.  Debugging would require manual log correlation\n"
        "  across three separate agents."
    )
    return all_spans


# ============================================================================
# SCENARIO 2: Tool Timeout with Retry
# ============================================================================

def scenario_tool_timeout() -> List[dict]:
    """A web_search tool call times out; the agent retries with degraded context.

    The first TOOL_CALL span shows ERROR/TIMEOUT status.
    A retry event is recorded.  The second attempt succeeds but returns
    partial results.  The subsequent LLM_CALL operates on degraded context.

    Without structured telemetry, you would see only the final output
    and not know that a timeout occurred or that context was degraded.
    """
    banner("SCENARIO 2: Tool Timeout with Retry")

    all_spans: List[dict] = []

    # -- Planner --
    planner = AgentTracer(agent_name="planner", framework="custom")

    with planner.start_task("Research fusion energy progress") as task:
        _sim_delay()

        with planner.start_planning("decompose_task") as plan:
            _sim_delay()
            with planner.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.03, 0.08)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 280)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 120)

        ctx = AgentContext.from_tracer(planner)

        # -- Researcher (with tool timeout) --
        researcher = AgentTracer(agent_name="researcher", framework="custom")

        with researcher.start_task("research: fusion energy") as rtask:
            rtask.trace_id = ctx.trace_id
            rtask.parent_span_id = ctx.parent_span_id

            # First tool call: TIMES OUT
            with researcher.start_tool_call("web_search") as tool1:
                time.sleep(0.15)  # Simulate the timeout wait
                tool1.set_attribute(ATTR_TOOL_INPUT, "fusion energy latest results 2025")
                tool1.set_attribute(ATTR_TOOL_SUCCESS, False)
                tool1.set_attribute(ATTR_TOOL_ERROR, "TimeoutError: request exceeded 30s limit")
                tool1.set_attribute(ATTR_TOOL_LATENCY_MS, 30000.0)
                tool1.set_status(SpanStatus.ERROR, "Tool call timed out after 30s")
                tool1.add_event(
                    "tool_timeout",
                    EventType.ERROR,
                    tool="web_search",
                    timeout_ms=30000,
                    message="web_search timed out; will retry with shorter query",
                )

            # Retry event on the task span
            rtask.add_event(
                "tool_retry",
                EventType.WARNING,
                retry_attempt=1,
                original_tool="web_search",
                strategy="simplified_query",
                message="Retrying web_search with simplified query after timeout",
            )

            # Second tool call: succeeds but with partial/degraded results
            with researcher.start_tool_call("web_search") as tool2:
                _sim_delay(0.03, 0.08)
                tool2.set_attribute(ATTR_TOOL_INPUT, "fusion energy")
                tool2.set_attribute(ATTR_TOOL_SUCCESS, True)
                tool2.set_attribute(ATTR_TOOL_LATENCY_MS, 2500.0)
                tool2.set_attribute(ATTR_TOOL_OUTPUT, "[2 results, partial coverage]")
                tool2.add_event(
                    "degraded_results",
                    EventType.WARNING,
                    result_count=2,
                    expected_count=10,
                    message="Retry returned fewer results than expected",
                )

            # LLM call with degraded context
            with researcher.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.05, 0.15)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 600)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 300)
                llm.set_attribute("llm.context_quality", "degraded")
                llm.set_attribute(
                    "llm.context_note",
                    "Operating on 2 search results instead of expected 10",
                )

        # -- Writer --
        writer = AgentTracer(agent_name="writer", framework="custom")

        with writer.start_task("write: fusion energy summary") as wtask:
            wtask.trace_id = ctx.trace_id
            wtask.parent_span_id = rtask.span_id

            with writer.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.05, 0.12)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 700)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 450)

    all_spans = (
        [s.to_dict() for s in planner.get_spans()]
        + [s.to_dict() for s in researcher.get_spans()]
        + [s.to_dict() for s in writer.get_spans()]
    )

    sub_banner("Trace Output")
    print_trace_tree(all_spans)

    sub_banner("Diagnosis")
    print(
        "  ROOT CAUSE: The first TOOL_CALL span for 'web_search' shows\n"
        "  status=ERROR with a TimeoutError after 30,000ms.  The agent\n"
        "  recorded a 'tool_retry' WARNING event, then retried with a\n"
        "  simplified query.  The retry succeeded but returned only 2\n"
        "  results instead of the expected 10.\n"
        "\n"
        "  WHAT TELEMETRY REVEALS:\n"
        "    - TOOL_CALL span 1: status=ERROR, tool.error='TimeoutError',\n"
        "      tool.latency_ms=30000\n"
        "    - WARNING event: 'tool_retry' with retry_attempt=1\n"
        "    - TOOL_CALL span 2: status=OK, but WARNING event shows\n"
        "      result_count=2 vs expected_count=10\n"
        "    - LLM_CALL span: context_quality='degraded'\n"
        "\n"
        "  WITHOUT AgentTelemetry: Framework-default logging might show\n"
        "  an error message for the timeout, but would not capture the\n"
        "  causal chain: timeout -> retry -> degraded results -> degraded\n"
        "  LLM context.  The span kinds (TOOL_CALL vs LLM_CALL) make it\n"
        "  immediately clear which pipeline stage failed and how the\n"
        "  failure propagated."
    )
    return all_spans


# ============================================================================
# SCENARIO 3: Cost Overrun
# ============================================================================

def scenario_cost_overrun() -> List[dict]:
    """A reasoning loop makes excessive LLM calls, blowing past a cost budget.

    The researcher enters a self-critique loop that keeps calling the LLM.
    A COST_THRESHOLD event fires when cumulative cost exceeds $1.00.
    The trace shows exactly which iteration pushed past the threshold
    and the cumulative cost at each step.

    Without structured telemetry, you would only see an unexpectedly
    large bill with no attribution to a specific agent or reasoning loop.
    """
    banner("SCENARIO 3: Cost Overrun")

    all_spans: List[dict] = []
    metrics = AgentMetrics(agent_name="researcher")

    # -- Planner --
    planner = AgentTracer(agent_name="planner", framework="custom")

    with planner.start_task("Deep analysis of AI safety research") as task:
        _sim_delay()

        with planner.start_planning("decompose_task") as plan:
            _sim_delay()
            with planner.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.02, 0.05)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 350)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 180)

        ctx = AgentContext.from_tracer(planner)

        # -- Researcher (with excessive reasoning loop) --
        researcher = AgentTracer(agent_name="researcher", framework="custom")

        with researcher.start_task("research: AI safety deep dive") as rtask:
            rtask.trace_id = ctx.trace_id
            rtask.parent_span_id = ctx.parent_span_id

            # Initial retrieval
            with researcher.start_retrieval("rag_search") as ret:
                _sim_delay(0.02, 0.05)
                ret.set_attribute("retrieval.relevance_score", 0.75)
                ret.set_attribute("retrieval.top_k", 10)

            # Reasoning loop: the agent keeps self-critiquing and calling the
            # LLM again.  Each iteration costs real money.
            cumulative_cost = 0.0
            cost_threshold = 1.00
            cost_threshold_fired = False
            num_iterations = 8  # Excessive -- normally 2-3 would suffice

            for i in range(num_iterations):
                iteration_label = f"iteration_{i+1}"

                with researcher.start_reasoning(
                    f"self_critique_{iteration_label}"
                ) as reason:
                    _sim_delay(0.01, 0.03)

                    # LLM call within the reasoning loop
                    with researcher.start_llm_call(model="gpt-4o") as llm:
                        # Simulate increasing token counts as context grows
                        input_tokens = 2000 + i * 800
                        output_tokens = 600 + i * 200
                        _sim_delay(0.03, 0.08)
                        llm.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
                        llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)

                        # Calculate cost manually for tracking
                        iteration_cost = estimate_cost("gpt-4o", input_tokens, output_tokens)
                        cumulative_cost += iteration_cost

                        llm.set_attribute("reasoning.iteration", i + 1)
                        llm.set_attribute("reasoning.cumulative_cost_usd", round(cumulative_cost, 6))

                        metrics.increment("agent.llm.call.count", model="gpt-4o")
                        metrics.increment("agent.cost.total_usd", value=iteration_cost)

                        # Check cost threshold
                        if cumulative_cost >= cost_threshold and not cost_threshold_fired:
                            cost_threshold_fired = True
                            llm.add_event(
                                "cost_threshold_exceeded",
                                EventType.COST_THRESHOLD,
                                threshold_usd=cost_threshold,
                                actual_usd=round(cumulative_cost, 4),
                                iteration=i + 1,
                                total_iterations_so_far=i + 1,
                                message=(
                                    f"Cumulative cost ${cumulative_cost:.4f} exceeds "
                                    f"threshold ${cost_threshold:.2f} at iteration {i+1}"
                                ),
                            )

                    # Self-critique event
                    reason.add_event(
                        "self_critique_result",
                        EventType.CUSTOM,
                        verdict="needs_improvement" if i < num_iterations - 1 else "acceptable",
                        iteration=i + 1,
                    )

            # Record total cost on the task span
            rtask.set_attribute("task.total_cost_usd", round(cumulative_cost, 6))
            rtask.set_attribute("task.llm_call_count", num_iterations)
            rtask.set_attribute(
                "task.cost_note",
                f"Reasoning loop ran {num_iterations} iterations; expected 2-3",
            )

        # -- Writer --
        writer = AgentTracer(agent_name="writer", framework="custom")

        with writer.start_task("write: AI safety analysis") as wtask:
            wtask.trace_id = ctx.trace_id
            wtask.parent_span_id = rtask.span_id

            with writer.start_llm_call(model="gpt-4o") as llm:
                _sim_delay(0.05, 0.1)
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 3000)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 1200)

    all_spans = (
        [s.to_dict() for s in planner.get_spans()]
        + [s.to_dict() for s in researcher.get_spans()]
        + [s.to_dict() for s in writer.get_spans()]
    )

    sub_banner("Trace Output")
    print_trace_tree(all_spans)

    # Show cost accumulation curve
    sub_banner("Cost Accumulation Detail")
    running_cost = 0.0
    print(f"  {'Iteration':<12} {'Input Tok':<12} {'Output Tok':<12} {'Iter Cost':>12} {'Cumulative':>12}  Note")
    print(f"  {'--------':<12} {'--------':<12} {'----------':<12} {'---------':>12} {'----------':>12}  ----")
    for i in range(num_iterations):
        input_tokens = 2000 + i * 800
        output_tokens = 600 + i * 200
        iter_cost = estimate_cost("gpt-4o", input_tokens, output_tokens)
        running_cost += iter_cost
        note = ""
        if running_cost >= cost_threshold and (running_cost - iter_cost) < cost_threshold:
            note = "<-- COST_THRESHOLD event fired here"
        print(
            f"  {i+1:<12} {input_tokens:<12} {output_tokens:<12} "
            f"${iter_cost:>10.6f} ${running_cost:>10.6f}  {note}"
        )

    sub_banner("Diagnosis")
    print(
        f"  ROOT CAUSE: The researcher's self-critique reasoning loop ran\n"
        f"  {num_iterations} iterations instead of the expected 2-3.  Each iteration\n"
        f"  made an LLM_CALL with increasing token counts (context growth).\n"
        f"  Total cost reached ${cumulative_cost:.4f}, exceeding the $1.00 threshold.\n"
        f"\n"
        f"  WHAT TELEMETRY REVEALS:\n"
        f"    - {num_iterations} REASONING spans, each containing an LLM_CALL\n"
        f"    - reasoning.iteration attribute on each LLM_CALL shows the loop count\n"
        f"    - reasoning.cumulative_cost_usd grows with each iteration\n"
        f"    - COST_THRESHOLD event fires at the exact iteration that exceeds $1.00\n"
        f"    - task.total_cost_usd on the TASK span shows final cost attribution\n"
        f"\n"
        f"  WITHOUT AgentTelemetry: You would see only the final bill total\n"
        f"  with no breakdown of which agent, which reasoning loop, or which\n"
        f"  iteration caused the overrun.  Framework-default logging does not\n"
        f"  track cumulative cost, does not fire threshold events, and does\n"
        f"  not attribute cost to specific reasoning patterns."
    )

    # Print metrics summary
    sub_banner("Metrics Summary")
    summary = metrics.summary()
    print(f"  Total LLM calls: {summary['counters'].get('agent.llm.call.count{agent.name=researcher,model=gpt-4o}', 'N/A')}")
    print(f"  Total cost (USD): ${summary['counters'].get('agent.cost.total_usd{agent.name=researcher}', 0):.6f}")

    return all_spans


# ============================================================================
# Summary Comparison Table
# ============================================================================

def print_comparison_table() -> None:
    """Print a table comparing diagnosis with vs without AgentTelemetry."""
    banner("COMPARISON: Diagnosis With vs Without AgentTelemetry")

    header = (
        f"  {'Fault Scenario':<28} {'Without AgentTelemetry':<34} "
        f"{'With AgentTelemetry':<34}"
    )
    sep = "  " + "-" * 94

    print(header)
    print(sep)

    rows = [
        (
            "Hallucinated Retrieval",
            "See bad output; no cause",
            "RETRIEVAL span: relevance=0.12",
        ),
        (
            "  Time to diagnose:",
            "30-60 min (log hunting)",
            "< 2 min (span inspection)",
        ),
        (
            "  Diagnostic accuracy:",
            "Low (guess at cause)",
            "High (exact span + event)",
        ),
        ("", "", ""),
        (
            "Tool Timeout + Retry",
            "See error log; miss retry",
            "TOOL_CALL ERROR -> retry -> OK",
        ),
        (
            "  Time to diagnose:",
            "15-30 min (correlate logs)",
            "< 1 min (trace waterfall)",
        ),
        (
            "  Diagnostic accuracy:",
            "Medium (find timeout only)",
            "High (full causal chain)",
        ),
        ("", "", ""),
        (
            "Cost Overrun",
            "See large bill; no breakdown",
            "LLM_CALL x8 + COST_THRESHOLD",
        ),
        (
            "  Time to diagnose:",
            "Hours (billing dashboard)",
            "< 1 min (cost attribution)",
        ),
        (
            "  Diagnostic accuracy:",
            "Low (no per-loop breakdown)",
            "High (iteration-level cost)",
        ),
    ]

    for col1, col2, col3 in rows:
        print(f"  {col1:<28} {col2:<34} {col3:<34}")

    print()
    print(
        "  KEY INSIGHT: Agent-specific span kinds (RETRIEVAL, TOOL_CALL,\n"
        "  LLM_CALL, REASONING) combined with semantic attributes (relevance\n"
        "  scores, cost, retry metadata) enable rapid root-cause diagnosis\n"
        "  that is impossible with generic framework logging alone."
    )


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    banner("AgentTelemetry -- Debugging Case Study")
    print(
        "  This script demonstrates three fault injection scenarios in a\n"
        "  multi-agent pipeline (planner -> researcher -> writer) and shows\n"
        "  how AgentTelemetry helps diagnose each fault.\n"
        "\n"
        "  No API keys or real LLM calls required. All operations are simulated.\n"
    )

    # Set random seed for reproducibility
    random.seed(42)

    # Run all three scenarios
    spans_1 = scenario_hallucinated_retrieval()
    spans_2 = scenario_tool_timeout()
    spans_3 = scenario_cost_overrun()

    # Print comparison table
    print_comparison_table()

    # Export all spans to a JSON Lines file
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "debugging_case_study_traces.jsonl")
    if os.path.exists(output_file):
        os.remove(output_file)

    exporter = JSONFileExporter(file_path=output_file)
    all_spans = spans_1 + spans_2 + spans_3
    for span_dict in all_spans:
        # Write each span as a JSON line
        with open(output_file, "a") as f:
            f.write(json.dumps(span_dict, default=str) + "\n")

    sub_banner("Export Summary")
    print(f"  Total spans exported: {len(all_spans)}")
    print(f"  Output file: {output_file}")
    print()

    # Span kind distribution
    kind_counts: Dict[str, int] = {}
    for s in all_spans:
        k = s["kind"]
        kind_counts[k] = kind_counts.get(k, 0) + 1
    print("  Span kind distribution:")
    for kind, count in sorted(kind_counts.items()):
        print(f"    {kind:<14} {count}")

    # Status distribution
    status_counts: Dict[str, int] = {}
    for s in all_spans:
        st = s["status"]
        status_counts[st] = status_counts.get(st, 0) + 1
    print()
    print("  Status distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"    {status:<14} {count}")

    print()
    print(SEPARATOR)
    print("  Done. All three fault scenarios demonstrated successfully.")
    print(SEPARATOR)
    print()


if __name__ == "__main__":
    main()
