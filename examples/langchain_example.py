#!/usr/bin/env python3
"""Auto-instrumentation example with LangChain.

This example shows how to use the LangChainInstrumentor to automatically
capture telemetry from LangChain without modifying your agent code.

Requirements:
    pip install agenttelemetry[langchain]
    pip install langchain-openai   # or another provider
    export OPENAI_API_KEY="sk-..."

If you do not have an API key, the script prints a helpful message and
exits gracefully.

Run:
    python -m examples.langchain_example
    # or
    python examples/langchain_example.py
"""

import os
import sys


def check_dependencies():
    """Verify that LangChain is installed before proceeding."""
    try:
        import langchain_core  # noqa: F401
    except ImportError:
        print(
            "This example requires LangChain.\n"
            "Install with:  pip install agenttelemetry[langchain] langchain-openai\n"
        )
        sys.exit(1)


def run_langchain_agent():
    """Demonstrate auto-instrumented LangChain agent with tools."""

    # -- Lazy imports (only after dependency check) ------------------------
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage

    from agenttelemetry.core.trace import AgentTracer
    from agenttelemetry.core.metrics import AgentMetrics
    from agenttelemetry.exporters.console import ConsoleExporter
    from agenttelemetry.exporters.json_file import JSONFileExporter
    from agenttelemetry.instrumentors.langchain import LangChainInstrumentor

    # -- Setup telemetry ---------------------------------------------------
    tracer = AgentTracer(
        agent_name="langchain-agent",
        framework="langchain",
        capture_content=False,  # do not log prompts/completions
    )
    metrics = AgentMetrics(agent_name="langchain-agent")

    console_exporter = ConsoleExporter(verbose=False)
    file_exporter = JSONFileExporter(
        file_path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "langchain_traces.jsonl",
        )
    )
    tracer.add_exporter(console_exporter)
    tracer.add_exporter(file_exporter)

    # -- Instrument LangChain (one line!) ----------------------------------
    instrumentor = LangChainInstrumentor(
        tracer=tracer,
        metrics=metrics,
        capture_content=False,
    )
    instrumentor.instrument()
    print(f"LangChain instrumented: {instrumentor.is_instrumented}")

    # -- Define tools ------------------------------------------------------
    @tool
    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        # Simulated response
        weathers = {
            "san francisco": "Foggy, 58F",
            "new york": "Sunny, 72F",
            "london": "Rainy, 55F",
        }
        return weathers.get(city.lower(), f"Unknown weather for {city}")

    @tool
    def get_population(city: str) -> str:
        """Get the population of a city."""
        populations = {
            "san francisco": "873,965",
            "new york": "8,336,817",
            "london": "8,982,000",
        }
        return populations.get(city.lower(), f"Unknown population for {city}")

    tools = [get_weather, get_population]

    # -- Check for API key -------------------------------------------------
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-..."):
        print()
        print("=" * 72)
        print("  No OPENAI_API_KEY found.")
        print()
        print("  This example requires a valid API key to call the LLM.")
        print("  Set it with:  export OPENAI_API_KEY='sk-...'")
        print()
        print("  Showing what the instrumented code looks like instead:")
        print("=" * 72)
        print()
        _show_simulated_run(tracer, metrics, tools)
        instrumentor.uninstrument()
        return

    # -- Build and run the agent -------------------------------------------
    try:
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_tool_calling_agent, AgentExecutor
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Use tools when needed."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        print()
        print("--- Running LangChain Agent (auto-instrumented) ---")
        print()

        result = executor.invoke({
            "input": "What is the weather and population of San Francisco?"
        })

        print()
        print(f"Agent output: {result['output']}")

    except Exception as exc:
        print(f"Error running agent: {exc}")
        print("Falling back to simulated run.")
        _show_simulated_run(tracer, metrics, tools)

    # -- Cleanup -----------------------------------------------------------
    instrumentor.uninstrument()
    print(f"\nLangChain uninstrumented: {not instrumentor.is_instrumented}")

    # -- Show metrics ------------------------------------------------------
    print()
    print("--- Metrics Summary ---")
    import json
    print(json.dumps(metrics.summary(), indent=2, default=str))


def _show_simulated_run(tracer, metrics, tools):
    """Show what auto-instrumented spans look like using manual tracing.

    This runs when no API key is available, so users can still see the
    telemetry output format without incurring any LLM costs.
    """
    import time
    import random
    from agenttelemetry.core.trace import (
        ATTR_LLM_INPUT_TOKENS,
        ATTR_LLM_OUTPUT_TOKENS,
        ATTR_TOOL_INPUT,
        ATTR_TOOL_OUTPUT,
        ATTR_TOOL_SUCCESS,
        ATTR_AGENT_TASK,
    )
    from agenttelemetry.core.events import EventType

    print("--- Simulated Auto-Instrumented Run ---")
    print("    (This is what the trace output looks like.)")
    print()

    with tracer.start_task(
        "AgentExecutor",
        **{ATTR_AGENT_TASK: "What is the weather and population of San Francisco?"},
    ) as task_span:
        metrics.increment("agent.task.count")

        # Simulated LLM call #1: decide which tools to call
        with tracer.start_llm_call(model="gpt-4o-mini") as llm_span:
            time.sleep(0.05)
            llm_span.set_attribute(ATTR_LLM_INPUT_TOKENS, 320)
            llm_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 85)
            metrics.increment("agent.llm.call.count", model="gpt-4o-mini")

        # Simulated tool call: get_weather
        with tracer.start_tool_call("get_weather") as tool_span:
            time.sleep(0.02)
            tool_span.set_attribute(ATTR_TOOL_INPUT, "San Francisco")
            tool_span.set_attribute(ATTR_TOOL_OUTPUT, "Foggy, 58F")
            tool_span.set_attribute(ATTR_TOOL_SUCCESS, True)
            metrics.increment("agent.tool.call.count", tool="get_weather")

        # Simulated tool call: get_population
        with tracer.start_tool_call("get_population") as tool_span:
            time.sleep(0.02)
            tool_span.set_attribute(ATTR_TOOL_INPUT, "San Francisco")
            tool_span.set_attribute(ATTR_TOOL_OUTPUT, "873,965")
            tool_span.set_attribute(ATTR_TOOL_SUCCESS, True)
            metrics.increment("agent.tool.call.count", tool="get_population")

        # Simulated LLM call #2: synthesize answer
        with tracer.start_llm_call(model="gpt-4o-mini") as llm_span:
            time.sleep(0.05)
            llm_span.set_attribute(ATTR_LLM_INPUT_TOKENS, 450)
            llm_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 120)
            metrics.increment("agent.llm.call.count", model="gpt-4o-mini")

    print()
    print("  The spans above were generated by simulated auto-instrumentation.")
    print("  With a real API key, LangChainInstrumentor captures these automatically.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("  AgentTelemetry -- LangChain Auto-Instrumentation Example")
    print("=" * 72)
    print()

    check_dependencies()
    run_langchain_agent()

    print()
    print("=" * 72)
    print("  Done.")
    print("=" * 72)


if __name__ == "__main__":
    main()
