#!/usr/bin/env python3
"""Multi-agent collaboration with context propagation.

This example simulates two agents working together:

  * Planner Agent   -- decomposes a task and delegates sub-tasks
  * Researcher Agent -- executes sub-tasks (search + summarize)

Key concepts demonstrated:
  - AgentContext for propagating trace context across agent boundaries
  - Inter-agent communication spans (AGENT_COMM)
  - Shared trace_id so all spans appear in a single unified trace
  - JSONFileExporter for writing traces to a .jsonl file

Run:
    python -m examples.multi_agent
    # or
    python examples/multi_agent.py

After running, inspect the generated ``multi_agent_traces.jsonl`` file to see
all spans from both agents sharing the same trace_id.
"""

import json
import os
import random
import time
from pathlib import Path

from agenttelemetry.core.trace import (
    AgentTracer,
    ATTR_AGENT_TASK,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    ATTR_INTERACTION_TYPE,
)
from agenttelemetry.core.context import AgentContext
from agenttelemetry.core.events import EventType
from agenttelemetry.core.metrics import AgentMetrics
from agenttelemetry.exporters.json_file import JSONFileExporter
from agenttelemetry.exporters.console import ConsoleExporter


# ---------------------------------------------------------------------------
# Simulated helpers
# ---------------------------------------------------------------------------

def simulate_llm(prompt: str, model: str = "gpt-4o") -> dict:
    """Fake LLM call with random latency and token counts."""
    time.sleep(random.uniform(0.05, 0.2))
    return {
        "completion": f"[Simulated {model} response to: {prompt[:50]}...]",
        "input_tokens": random.randint(200, 500),
        "output_tokens": random.randint(80, 200),
    }


def simulate_search(query: str) -> str:
    """Fake web search."""
    time.sleep(random.uniform(0.03, 0.1))
    return json.dumps([
        {"title": f"Result for: {query}", "snippet": "Lorem ipsum ..."},
    ])


# ---------------------------------------------------------------------------
# Researcher Agent
# ---------------------------------------------------------------------------

def researcher_agent(
    sub_task: str,
    parent_context: AgentContext,
    exporter: JSONFileExporter,
) -> str:
    """Run the researcher agent, inheriting trace context from the planner.

    Args:
        sub_task: The sub-task description to research.
        parent_context: Propagated context from the planner agent.
        exporter: Shared exporter so all spans go to the same file.

    Returns:
        A simulated summary string.
    """
    # Create a tracer for this agent, sharing the parent's trace_id
    tracer = AgentTracer(
        agent_name="researcher",
        framework="custom",
    )
    tracer.add_exporter(exporter)
    tracer.add_exporter(ConsoleExporter())

    # Inject parent context so spans share the same trace_id.
    # We do this by starting a task that manually re-uses the parent trace_id.
    # The tracer's _make_span for TASK normally generates a new trace_id,
    # so we use start_reasoning (a child span kind) under a manually
    # constructed root that carries the propagated trace.

    with tracer.start_task(f"research: {sub_task}", **{ATTR_AGENT_TASK: sub_task}) as task_span:
        # Overwrite the auto-generated trace_id with the propagated one
        task_span.trace_id = parent_context.trace_id
        task_span.parent_span_id = parent_context.parent_span_id

        # Tool call: search
        with tracer.start_tool_call("web_search") as tool_span:
            tool_span.set_attribute(ATTR_TOOL_INPUT, sub_task)
            results = simulate_search(sub_task)
            tool_span.set_attribute(ATTR_TOOL_OUTPUT, results)
            tool_span.set_attribute(ATTR_TOOL_SUCCESS, True)

        # LLM call: summarize
        with tracer.start_llm_call(model="gpt-4o-mini") as llm_span:
            response = simulate_llm(
                f"Summarize search results for: {sub_task}", model="gpt-4o-mini"
            )
            llm_span.set_attribute(ATTR_LLM_INPUT_TOKENS, response["input_tokens"])
            llm_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, response["output_tokens"])

    return response["completion"]


# ---------------------------------------------------------------------------
# Planner Agent
# ---------------------------------------------------------------------------

def planner_agent(task: str, exporter: JSONFileExporter) -> None:
    """Run the planner agent that decomposes a task and delegates."""

    tracer = AgentTracer(
        agent_name="planner",
        framework="custom",
    )
    tracer.add_exporter(exporter)
    tracer.add_exporter(ConsoleExporter())

    metrics = AgentMetrics(agent_name="planner")

    with tracer.start_task(task, **{ATTR_AGENT_TASK: task}) as task_span:
        metrics.increment("agent.task.count")

        # Step 1: Plan -- break the task into sub-tasks
        with tracer.start_planning("decompose_task") as plan_span:
            with tracer.start_llm_call(model="gpt-4o") as llm_span:
                plan_response = simulate_llm(f"Break this task into sub-tasks: {task}")
                llm_span.set_attribute(ATTR_LLM_INPUT_TOKENS, plan_response["input_tokens"])
                llm_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, plan_response["output_tokens"])

            sub_tasks = [
                "Find recent breakthroughs in quantum computing",
                "Summarize latest developments in fusion energy",
                "Review recent advances in AI reasoning",
            ]
            plan_span.add_event(
                "plan_created",
                EventType.PLANNING_END,
                sub_tasks=sub_tasks,
            )

        # Step 2: Delegate each sub-task to the researcher agent
        results = []
        for i, sub_task in enumerate(sub_tasks):
            # Create a communication span for the delegation
            with tracer.start_agent_comm(
                target_agent="researcher",
                **{ATTR_INTERACTION_TYPE: "delegation"},
            ) as comm_span:
                comm_span.add_event(
                    "delegate_task",
                    EventType.AGENT_MESSAGE,
                    sub_task=sub_task,
                    sub_task_index=i,
                )

                # Propagate context to the researcher
                ctx = AgentContext.from_tracer(tracer)
                if ctx is None:
                    # Fallback -- shouldn't happen since we have active spans
                    ctx = AgentContext(
                        trace_id=task_span.trace_id,
                        parent_span_id=comm_span.span_id,
                        source_agent="planner",
                    )
                else:
                    # Demonstrate carrier serialization (what you'd do over HTTP)
                    carrier = ctx.to_carrier()
                    print(f"\n  [context propagation] carrier = {carrier}")
                    ctx = AgentContext.from_carrier(carrier)

                # Run the researcher with propagated context
                result = researcher_agent(sub_task, ctx, exporter)
                results.append(result)

                comm_span.add_event(
                    "result_received",
                    EventType.AGENT_MESSAGE,
                    result_preview=result[:80],
                )

        # Step 3: Final synthesis
        with tracer.start_llm_call(model="gpt-4o") as synth_span:
            combined = "\n".join(results)
            synth_response = simulate_llm(f"Synthesize these findings:\n{combined}")
            synth_span.set_attribute(ATTR_LLM_INPUT_TOKENS, synth_response["input_tokens"])
            synth_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, synth_response["output_tokens"])

        # Step 4: Reflect on completeness
        with tracer.start_reasoning("evaluate_completeness") as reflect_span:
            time.sleep(0.02)
            reflect_span.add_event(
                "evaluation",
                EventType.CUSTOM,
                coverage="3/3 sub-tasks completed",
                quality="satisfactory",
            )

    return synth_response["completion"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "multi_agent_traces.jsonl",
    )
    # Remove old output if present
    if os.path.exists(output_file):
        os.remove(output_file)

    exporter = JSONFileExporter(file_path=output_file)

    print("=" * 72)
    print("  AgentTelemetry -- Multi-Agent Example")
    print("=" * 72)
    print()
    print("--- Trace Output ---")
    print()

    result = planner_agent(
        task="Research and summarize breakthroughs in science and technology",
        exporter=exporter,
    )

    # -- Read back the exported traces and show summary --------------------
    print()
    print("--- Exported Trace File ---")
    print()
    spans = exporter.read_traces()
    print(f"  File:  {output_file}")
    print(f"  Spans: {len(spans)}")
    print()

    # Group by trace_id to verify context propagation
    traces = {}
    for span in spans:
        tid = span["trace_id"]
        if tid not in traces:
            traces[tid] = []
        traces[tid].append(span)

    print(f"  Unique trace IDs: {len(traces)}")
    for tid, trace_spans in traces.items():
        agents = set(s["attributes"].get("agent.name", "?") for s in trace_spans)
        kinds = [s["kind"] for s in trace_spans]
        print(f"    trace {tid[:12]}...  agents={agents}  spans={len(trace_spans)}")
        for s in trace_spans:
            agent = s["attributes"].get("agent.name", "?")
            print(f"      [{agent:<12}] {s['kind']:<12} {s['name']}")

    print()
    print("=" * 72)
    print(f"  Done. Traces written to {output_file}")
    print("=" * 72)


if __name__ == "__main__":
    main()
