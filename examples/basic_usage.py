#!/usr/bin/env python3
"""Basic AgentTelemetry usage -- manual instrumentation.

This example simulates an AI agent that:
  1. Receives a task ("Summarize recent AI news")
  2. Plans its approach
  3. Calls a search tool to find articles
  4. Makes an LLM call to summarize the results
  5. Reflects on quality before returning

No real LLM or tools are needed -- all calls are simulated so you can run
this script standalone to see how tracing and metrics work.

Run:
    python -m examples.basic_usage
    # or
    python examples/basic_usage.py
"""

import json
import random
import time

from agenttelemetry.core.trace import (
    AgentTracer,
    SpanStatus,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_TEMPERATURE,
    ATTR_LLM_PROMPT,
    ATTR_LLM_COMPLETION,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    ATTR_AGENT_TASK,
)
from agenttelemetry.core.events import EventType
from agenttelemetry.core.metrics import AgentMetrics
from agenttelemetry.exporters.console import ConsoleExporter


# ---------------------------------------------------------------------------
# Simulated tool and LLM helpers
# ---------------------------------------------------------------------------

def simulate_web_search(query: str) -> str:
    """Pretend to search the web. Returns fake results after a short delay."""
    time.sleep(random.uniform(0.05, 0.15))
    return json.dumps([
        {"title": "GPT-5 Released", "snippet": "OpenAI announces GPT-5 ..."},
        {"title": "Claude Opus 4 Benchmarks", "snippet": "Anthropic's Claude Opus 4 ..."},
        {"title": "Open-Source LLMs Surge", "snippet": "Meta and Mistral release ..."},
    ])


def simulate_llm_call(prompt: str) -> dict:
    """Pretend to call an LLM. Returns a fake completion and token counts."""
    time.sleep(random.uniform(0.1, 0.3))
    return {
        "completion": (
            "Here is a summary of recent AI news: (1) GPT-5 was released with "
            "improved reasoning. (2) Claude Opus 4 set new benchmarks in coding "
            "and analysis. (3) Open-source LLMs from Meta and Mistral continue "
            "to close the gap with proprietary models."
        ),
        "input_tokens": random.randint(400, 600),
        "output_tokens": random.randint(100, 250),
    }


# ---------------------------------------------------------------------------
# Main agent logic with tracing
# ---------------------------------------------------------------------------

def run_agent():
    """Run a simple research agent with full telemetry."""

    # -- Setup tracer and exporter -----------------------------------------
    tracer = AgentTracer(
        agent_name="researcher",
        framework="custom",
        framework_version="1.0.0",
        capture_content=True,  # record prompts and completions (opt-in)
    )
    tracer.add_exporter(ConsoleExporter(verbose=False))

    # -- Setup metrics collector -------------------------------------------
    metrics = AgentMetrics(agent_name="researcher")

    task_description = "Summarize recent AI news"

    print("=" * 72)
    print(f"  AgentTelemetry -- Basic Usage Example")
    print(f"  Task: {task_description}")
    print("=" * 72)
    print()
    print("--- Trace Output (each line = one completed span) ---")
    print()

    # -- Execute the agent task --------------------------------------------
    with tracer.start_task(task_description, **{ATTR_AGENT_TASK: task_description}) as task_span:
        metrics.increment("agent.task.count")

        # Step 1: Planning
        with tracer.start_planning("plan_research") as plan_span:
            time.sleep(0.02)  # simulate thinking
            plan_span.add_event(
                "plan_created",
                EventType.PLANNING_END,
                steps=["search_web", "summarize", "reflect"],
            )

        # Step 2: Tool call -- web search
        with tracer.start_tool_call("web_search") as tool_span:
            query = "latest AI news 2025"
            tool_span.set_attribute(ATTR_TOOL_INPUT, query)
            tool_span.add_event("search_started", EventType.TOOL_START, query=query)

            results = simulate_web_search(query)

            tool_span.set_attribute(ATTR_TOOL_OUTPUT, results)
            tool_span.set_attribute(ATTR_TOOL_SUCCESS, True)
            tool_span.add_event("search_completed", EventType.TOOL_END, num_results=3)

            metrics.increment("agent.tool.call.count", tool="web_search")
            metrics.record("agent.tool.latency_ms", tool_span.duration_ms, tool="web_search")

        # Step 3: LLM call -- summarize the search results
        with tracer.start_llm_call(model="gpt-4o") as llm_span:
            prompt = f"Summarize these articles:\n{results}"
            llm_span.set_attribute(ATTR_LLM_TEMPERATURE, 0.3)

            # Capture content only if the tracer allows it
            if tracer.capture_content:
                llm_span.set_attribute(ATTR_LLM_PROMPT, prompt)

            llm_span.add_event("llm_request_sent", EventType.LLM_START, model="gpt-4o")
            response = simulate_llm_call(prompt)

            llm_span.set_attribute(ATTR_LLM_INPUT_TOKENS, response["input_tokens"])
            llm_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, response["output_tokens"])
            if tracer.capture_content:
                llm_span.set_attribute(ATTR_LLM_COMPLETION, response["completion"])

            llm_span.add_event("llm_response_received", EventType.LLM_END)

            # Record metrics
            metrics.increment("agent.llm.call.count", model="gpt-4o")
            metrics.increment("agent.llm.tokens.input", value=response["input_tokens"], model="gpt-4o")
            metrics.increment("agent.llm.tokens.output", value=response["output_tokens"], model="gpt-4o")
            metrics.record("agent.llm.latency_ms", llm_span.duration_ms, model="gpt-4o")

        # Step 4: Reasoning -- reflect on quality
        with tracer.start_reasoning("quality_check") as reason_span:
            time.sleep(0.01)
            reason_span.add_event(
                "quality_assessment",
                EventType.CUSTOM,
                verdict="pass",
                confidence=0.92,
            )

        # Step 5: Second LLM call -- polish the summary
        with tracer.start_llm_call(model="gpt-4o-mini") as llm2_span:
            prompt2 = f"Polish this summary for clarity:\n{response['completion']}"
            if tracer.capture_content:
                llm2_span.set_attribute(ATTR_LLM_PROMPT, prompt2)

            response2 = simulate_llm_call(prompt2)
            llm2_span.set_attribute(ATTR_LLM_INPUT_TOKENS, response2["input_tokens"])
            llm2_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, response2["output_tokens"])

            metrics.increment("agent.llm.call.count", model="gpt-4o-mini")
            metrics.increment("agent.llm.tokens.input", value=response2["input_tokens"], model="gpt-4o-mini")
            metrics.increment("agent.llm.tokens.output", value=response2["output_tokens"], model="gpt-4o-mini")
            metrics.record("agent.llm.latency_ms", llm2_span.duration_ms, model="gpt-4o-mini")

    # -- Print metrics summary ---------------------------------------------
    print()
    print("--- Metrics Summary ---")
    print()
    summary = metrics.summary()
    for section, data in summary.items():
        if data:
            print(f"  {section}:")
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        print(f"    {key}:")
                        for k, v in value.items():
                            print(f"      {k}: {v:.2f}" if isinstance(v, float) else f"      {k}: {v}")
                    else:
                        print(f"    {key}: {value:.4f}" if isinstance(value, float) else f"    {key}: {value}")
            print()

    # -- Print cost breakdown from trace spans -----------------------------
    print("--- Cost Breakdown (from trace spans) ---")
    print()
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    for span in tracer.get_spans():
        if span.cost_usd > 0:
            print(f"  {span.name:<30} ${span.cost_usd:.6f}  "
                  f"({span.input_tokens} in / {span.output_tokens} out)")
            total_cost += span.cost_usd
            total_input_tokens += span.input_tokens
            total_output_tokens += span.output_tokens
    print(f"  {'':->50}")
    print(f"  {'TOTAL':<30} ${total_cost:.6f}  "
          f"({total_input_tokens} in / {total_output_tokens} out)")
    print()

    # -- Print full trace (verbose JSON for one span) ----------------------
    print("--- Sample Span (verbose JSON) ---")
    print()
    # Show the first LLM call span in full detail
    llm_spans = [s for s in tracer.get_spans() if s.kind.value == "llm_call"]
    if llm_spans:
        print(json.dumps(llm_spans[0].to_dict(), indent=2, default=str))
    print()

    print("=" * 72)
    print("  Done. All spans were exported to console.")
    print("=" * 72)


if __name__ == "__main__":
    run_agent()
