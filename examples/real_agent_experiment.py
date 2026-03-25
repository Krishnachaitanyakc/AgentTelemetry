#!/usr/bin/env python3
"""
Real Agent Experiment for EuroMLSys 2026 Paper
================================================
Runs a tool-calling agent using the Anthropic SDK directly,
instrumented with AgentTelemetry's ClaudeAgentInstrumentor.
Captures traces via JSONFileExporter and measures overhead vs.
an uninstrumented baseline.

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=<your-key>

Usage:
    PYTHONPATH=src python examples/real_agent_experiment.py

If no API key is available, falls back to a simulated agent run.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agenttelemetry.core.trace import AgentTracer, AgentSpanKind
from agenttelemetry.core.metrics import AgentMetrics
from agenttelemetry.exporters.json_file import JSONFileExporter
from agenttelemetry.exporters.console import ConsoleExporter


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_RUNS = 10
MODEL = "claude-sonnet-4-20250514"
TRACE_OUTPUT = os.path.join(
    os.path.dirname(__file__), "experiment_traces.jsonl"
)

# Tool definitions for the Anthropic API
TOOLS = [
    {
        "name": "search",
        "description": "Search for factual information about a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Calculate a mathematical expression.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate",
                }
            },
            "required": ["expression"],
        },
    },
]


def execute_tool(name, input_data):
    """Execute a tool and return the result string."""
    if name == "search":
        query = input_data.get("query", "")
        if "population" in query.lower() and "france" in query.lower():
            return "The population of France in 2024 is approximately 67.97 million people."
        return "Search results for: " + query
    elif name == "calculator":
        expr = input_data.get("expression", "")
        try:
            result = eval(expr)  # Safe for controlled experiment
            return str(result)
        except Exception as e:
            return "Error: " + str(e)
    return "Unknown tool"


# ---------------------------------------------------------------------------
# Real agent using Anthropic SDK directly
# ---------------------------------------------------------------------------
def run_real_agent(client, question):
    """Run an agentic loop using Anthropic messages API with tool use."""
    messages = [{"role": "user", "content": question}]
    system = ("You are a helpful assistant. Use the provided tools to "
              "answer questions. Use search first, then calculator if "
              "needed. Be concise.")

    for _ in range(5):  # max iterations
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Check if we're done (no tool use)
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        # Process tool use blocks
        tool_results = []
        has_tool_use = False
        for block in response.content:
            if block.type == "tool_use":
                has_tool_use = True
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if not has_tool_use:
            # No tool use and not end_turn — extract text
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        # Add assistant message and tool results
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return "Max iterations reached"


# ---------------------------------------------------------------------------
# Simulated agent (fallback when no API key)
# ---------------------------------------------------------------------------
def run_simulated_agent(tracer=None):
    """Simulate a multi-step agent: search -> calculate -> answer."""
    if tracer is None:
        time.sleep(0.002)
        time.sleep(0.001)
        time.sleep(0.002)
        return "The answer is 42."

    with tracer.start_task("answer_question") as task:
        with tracer.start_reasoning("analyze_question") as r:
            time.sleep(0.0005)
            r.set_attribute("reasoning.strategy", "decompose")

        with tracer.start_llm_call(model=MODEL) as llm:
            time.sleep(0.002)
            llm.set_attribute("llm.input_tokens", 350)
            llm.set_attribute("llm.output_tokens", 120)
            llm.set_attribute("llm.temperature", 0.0)

        with tracer.start_tool_call("web_search") as tc:
            time.sleep(0.001)
            tc.set_attribute("tool.input", "population of France 2024")
            tc.set_attribute("tool.output", "67.97 million")
            tc.set_attribute("tool.success", True)

        with tracer.start_tool_call("calculator") as tc:
            time.sleep(0.0005)
            tc.set_attribute("tool.input", "67.97 * 1000000")
            tc.set_attribute("tool.output", "67970000")
            tc.set_attribute("tool.success", True)

        with tracer.start_llm_call(model=MODEL) as llm:
            time.sleep(0.002)
            llm.set_attribute("llm.input_tokens", 580)
            llm.set_attribute("llm.output_tokens", 95)
            llm.set_attribute("llm.temperature", 0.0)

        with tracer.start_reasoning("verify_answer") as r:
            time.sleep(0.0003)
            r.set_attribute("reasoning.confidence", 0.95)

    return "The population of France is approximately 67.97 million."


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------
def run_experiment():
    """Run the full experiment: instrumented vs uninstrumented."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    use_real = False
    client = None

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            # Quick validation
            client.messages.create(
                model=MODEL, max_tokens=5,
                messages=[{"role": "user", "content": "Hi"}],
            )
            use_real = True
            print("[INFO] Using real Anthropic Claude agent (Sonnet 4)")
        except Exception as e:
            print(f"[WARN] Anthropic API error: {e}")
            print("[INFO] Falling back to simulated agent")
    else:
        print("[INFO] No ANTHROPIC_API_KEY; using simulated agent")

    question = ("What is the population of France and what is that "
                "number divided by 1000?")

    # Clean up previous traces
    if os.path.exists(TRACE_OUTPUT):
        os.remove(TRACE_OUTPUT)

    # ----- Phase 1: Uninstrumented baseline -----
    print("\n" + "=" * 60)
    print("Phase 1: Uninstrumented baseline ({} runs)".format(N_RUNS))
    print("=" * 60)

    baseline_times = []
    for i in range(N_RUNS):
        t0 = time.perf_counter()
        if use_real:
            run_real_agent(client, question)
        else:
            run_simulated_agent(tracer=None)
        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000
        baseline_times.append(elapsed_ms)
        print("  Run {:2d}: {:.2f} ms".format(i + 1, elapsed_ms))

    # ----- Phase 2: Instrumented runs -----
    print("\n" + "=" * 60)
    print("Phase 2: Instrumented with AgentTelemetry ({} runs)".format(
        N_RUNS))
    print("=" * 60)

    instrumented_times = []
    total_spans = 0
    json_exporter = JSONFileExporter(file_path=TRACE_OUTPUT)

    if use_real:
        # Use ClaudeAgentInstrumentor for Anthropic SDK
        try:
            from agenttelemetry.instrumentors.claude_agent import (
                ClaudeAgentInstrumentor,
            )

            inst = ClaudeAgentInstrumentor(capture_content=False)
            inst.tracer.add_exporter(json_exporter)
            inst.instrument()

            for i in range(N_RUNS):
                t0 = time.perf_counter()
                run_real_agent(client, question)
                t1 = time.perf_counter()
                elapsed_ms = (t1 - t0) * 1000
                instrumented_times.append(elapsed_ms)
                spans = inst.tracer.get_spans()
                total_spans += len(spans)
                print("  Run {:2d}: {:.2f} ms  (spans: {})".format(
                    i + 1, elapsed_ms, len(spans)))
                inst.tracer.clear_spans()

            inst.uninstrument()
        except ImportError:
            print("[WARN] ClaudeAgentInstrumentor not available")
            use_real = False

    if not use_real:
        for i in range(N_RUNS):
            tracer = AgentTracer(
                agent_name="researcher",
                framework="simulated",
                capture_content=False,
            )
            tracer.add_exporter(json_exporter)

            t0 = time.perf_counter()
            run_simulated_agent(tracer=tracer)
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000
            instrumented_times.append(elapsed_ms)
            spans = tracer.get_spans()
            total_spans += len(spans)
            print("  Run {:2d}: {:.2f} ms  (spans: {})".format(
                i + 1, elapsed_ms, len(spans)))

    # ----- Phase 3: Analyze results -----
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    baseline_mean = statistics.mean(baseline_times)
    baseline_std = (statistics.stdev(baseline_times)
                    if len(baseline_times) > 1 else 0)
    inst_mean = statistics.mean(instrumented_times)
    inst_std = (statistics.stdev(instrumented_times)
                if len(instrumented_times) > 1 else 0)

    overhead_ms = inst_mean - baseline_mean
    overhead_pct = ((overhead_ms / baseline_mean * 100)
                    if baseline_mean > 0 else 0)
    avg_spans = total_spans / N_RUNS

    agent_label = ("Real (Anthropic Claude Sonnet)" if use_real
                   else "Simulated")
    print("  Agent type:        {}".format(agent_label))
    print("  Runs per phase:    {}".format(N_RUNS))
    print("  Baseline mean:     {:.2f} +/- {:.2f} ms".format(
        baseline_mean, baseline_std))
    print("  Instrumented mean: {:.2f} +/- {:.2f} ms".format(
        inst_mean, inst_std))
    print("  Overhead:          {:.2f} ms ({:.3f}%)".format(
        overhead_ms, overhead_pct))
    print("  Avg spans/run:     {:.1f}".format(avg_spans))
    print("  Total spans:       {}".format(total_spans))

    # ----- Phase 4: Analyze trace structure -----
    print("\n" + "=" * 60)
    print("Trace Structure Analysis")
    print("=" * 60)

    kind_counts = {}
    token_totals = {"input": 0, "output": 0}
    total_cost = 0.0

    if os.path.exists(TRACE_OUTPUT):
        traces = {}
        with open(TRACE_OUTPUT) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                span = json.loads(line)
                tid = span.get("trace_id", "unknown")
                traces.setdefault(tid, []).append(span)

        print("  Unique traces:     {}".format(len(traces)))

        for tid, spans in traces.items():
            for span in spans:
                kind = span.get("kind", "UNKNOWN")
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
                attrs = span.get("attributes", {})
                token_totals["input"] += attrs.get(
                    "llm.input_tokens", 0)
                token_totals["output"] += attrs.get(
                    "llm.output_tokens", 0)
                total_cost += attrs.get("llm.cost_usd", 0)

        print("  Span kind distribution:")
        for kind, count in sorted(kind_counts.items()):
            print("    {:20s}: {}".format(kind, count))

        print("  Total input tokens:  {}".format(token_totals["input"]))
        print("  Total output tokens: {}".format(token_totals["output"]))
        print("  Total estimated cost: ${:.4f}".format(total_cost))

        # Show one sample trace structure
        sample_tid = list(traces.keys())[0]
        sample_spans = traces[sample_tid]
        print("\n  Sample trace ({}...):".format(sample_tid[:16]))
        for span in sample_spans:
            kind = span.get("kind", "?")
            name = span.get("name", "?")
            dur = span.get("duration_ms", 0)
            status = span.get("status", "?")
            indent = "    "
            if span.get("parent_span_id"):
                indent = "      "
            print("  {}[{}] {} ({:.1f}ms, {})".format(
                indent, kind, name, dur, status))

    # ----- Save summary as JSON -----
    summary = {
        "agent_type": ("real_anthropic_claude" if use_real
                       else "simulated"),
        "model": MODEL if use_real else "simulated",
        "n_runs": N_RUNS,
        "baseline_mean_ms": round(baseline_mean, 2),
        "baseline_std_ms": round(baseline_std, 2),
        "instrumented_mean_ms": round(inst_mean, 2),
        "instrumented_std_ms": round(inst_std, 2),
        "overhead_ms": round(overhead_ms, 2),
        "overhead_pct": round(overhead_pct, 3),
        "avg_spans_per_run": round(avg_spans, 1),
        "total_spans": total_spans,
        "span_kind_distribution": kind_counts,
        "total_input_tokens": token_totals["input"],
        "total_output_tokens": token_totals["output"],
        "total_cost_usd": round(total_cost, 4),
    }

    summary_path = os.path.join(
        os.path.dirname(__file__), "experiment_summary.json"
    )
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print("\n  Summary saved to: {}".format(summary_path))
    print("  Traces saved to:  {}".format(TRACE_OUTPUT))


if __name__ == "__main__":
    run_experiment()
