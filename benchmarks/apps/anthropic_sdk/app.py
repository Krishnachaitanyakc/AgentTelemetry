"""Anthropic SDK direct agent using manual AgentTelemetry instrumentation.

Simulates direct use of the Anthropic SDK for tool-calling:
1. LLM_CALL spans with llm.provider=anthropic
2. TOOL_CALL spans for tool use blocks
3. Simple loop: call model -> maybe use tool -> repeat
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

_BENCHMARKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = os.path.dirname(_BENCHMARKS_DIR)
_SRC_DIR = os.path.join(_ROOT_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from agenttelemetry import configure, start_agent_span, AgentSpanKind, AgentTelemetryProvider
from agenttelemetry.core.spans import (
    AGENT_NAME, AGENT_FRAMEWORK, AGENT_TASK,
    LLM_MODEL, LLM_PROVIDER, LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS, LLM_COST,
    TOOL_NAME, TOOL_STATUS, TOOL_LATENCY_MS,
    DELEGATION_SOURCE_AGENT, DELEGATION_TARGET_AGENT,
    estimate_cost,
)

# -- Mock tools ---------------------------------------------------------------

AVAILABLE_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Perform mathematical calculations",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression"},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "delegate_task",
        "description": "Delegate a sub-task to another agent",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "Target agent name"},
                "task": {"type": "string", "description": "Task to delegate"},
            },
            "required": ["agent", "task"],
        },
    },
]


def _execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a mock tool and return results."""
    if tool_input.get("__fault__") == "tool_failure":
        raise RuntimeError(f"Tool '{tool_name}' failed: simulated error")
    results = {
        "web_search": {"results": [{"title": "Result 1", "snippet": "Found relevant info"}], "count": 1},
        "calculator": {"result": 42.0},
    }
    return results.get(tool_name, {"status": "ok"})


# -- Agent logic --------------------------------------------------------------

def run_anthropic_agent(
    task: str = "Analyze the key themes in this document",
    mock_client: Any = None,
    provider: Optional[AgentTelemetryProvider] = None,
    model: str = "claude-sonnet-4",
    max_iterations: int = 5,
    fault_injector: Any = None,
) -> Dict[str, Any]:
    """Run an Anthropic SDK-style tool-calling agent with manual instrumentation.

    Simulates the standard Anthropic SDK agentic loop:
    call Claude -> check for tool_use blocks -> execute tools -> feed results back

    Args:
        task: The task for the agent to perform.
        mock_client: A MockAnthropicClient instance.
        provider: Pre-configured AgentTelemetryProvider, or creates one.
        model: Model name for LLM calls.
        max_iterations: Maximum agent loop iterations.

    Returns:
        Dict with agent results and telemetry metadata.
    """
    own_provider = provider is None
    if own_provider:
        provider = configure(service_name="anthropic-sdk", console=True)

    tracer = provider.get_tracer()
    results: Dict[str, Any] = {"steps": [], "final_answer": None, "iterations": 0}

    messages: List[Dict[str, Any]] = [{"role": "user", "content": task}]
    iteration = 0
    current_agent = "anthropic-agent"

    while iteration < max_iterations:
        iteration += 1

        # LLM call span
        with start_agent_span(f"anthropic-call-{iteration}", AgentSpanKind.LLM_CALL, tracer=tracer,
                              attributes={
                                  LLM_MODEL: model,
                                  LLM_PROVIDER: "anthropic",
                              }) as llm_span:
            if mock_client:
                try:
                    response = mock_client.messages.create(
                        model=model,
                        max_tokens=1024,
                        messages=messages,
                        tools=AVAILABLE_TOOLS,
                    )
                except TimeoutError as e:
                    from opentelemetry.trace import StatusCode
                    llm_span.set_status(StatusCode.ERROR, f"Timeout: {e}")
                    llm_span.record_exception(e)
                    llm_span.set_attribute(LLM_INPUT_TOKENS, 0)
                    llm_span.set_attribute(LLM_OUTPUT_TOKENS, 0)
                    results["steps"].append({"type": "llm_timeout", "error": str(e)})
                    break

                llm_span.set_attribute(LLM_INPUT_TOKENS, response.usage.input_tokens)
                llm_span.set_attribute(LLM_OUTPUT_TOKENS, response.usage.output_tokens)
                cost = estimate_cost(model, response.usage.input_tokens, response.usage.output_tokens)
                llm_span.set_attribute(LLM_COST, cost)

                has_tool_use = False
                for block in response.content:
                    if block.type == "tool_use":
                        has_tool_use = True

                        if block.name == "delegate_task":
                            target_agent = block.input.get("agent", "unknown")
                            with start_agent_span(f"delegate-{current_agent}-to-{target_agent}",
                                                  AgentSpanKind.DELEGATION, tracer=tracer,
                                                  attributes={
                                                      DELEGATION_SOURCE_AGENT: current_agent,
                                                      DELEGATION_TARGET_AGENT: target_agent,
                                                  }):
                                results["steps"].append({
                                    "type": "delegation",
                                    "source": current_agent,
                                    "target": target_agent,
                                })
                            current_agent = target_agent
                            messages.append({"role": "assistant", "content": response.content})
                            messages.append({
                                "role": "user",
                                "content": [{"type": "tool_result", "tool_use_id": block.id,
                                             "content": f"Delegated to {target_agent}"}],
                            })
                            continue

                        # Execute tool
                        tool_start = time.time()
                        with start_agent_span(f"tool-{block.name}", AgentSpanKind.TOOL_CALL, tracer=tracer,
                                              attributes={TOOL_NAME: block.name}) as tool_span:
                            try:
                                tool_result = _execute_tool(block.name, block.input)
                                tool_span.set_attribute(TOOL_STATUS, "success")
                                tool_span.set_attribute(TOOL_LATENCY_MS, (time.time() - tool_start) * 1000)
                                results["steps"].append({
                                    "type": "tool_call", "tool": block.name, "status": "success",
                                })
                            except Exception as e:
                                tool_span.set_attribute(TOOL_STATUS, "error")
                                tool_span.set_attribute(TOOL_LATENCY_MS, (time.time() - tool_start) * 1000)
                                tool_result = {"error": str(e)}
                                results["steps"].append({
                                    "type": "tool_call", "tool": block.name, "status": "error", "error": str(e),
                                })

                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({
                            "role": "user",
                            "content": [{"type": "tool_result", "tool_use_id": block.id,
                                         "content": str(tool_result)}],
                        })

                if not has_tool_use:
                    final_text = response.content[0].text if response.content else ""
                    results["final_answer"] = final_text
                    results["steps"].append({"type": "final_answer", "text": final_text[:100]})
                    break
            else:
                llm_span.set_attribute(LLM_INPUT_TOKENS, 500)
                llm_span.set_attribute(LLM_OUTPUT_TOKENS, 200)
                results["final_answer"] = "Demo response without mock client."
                break

    results["iterations"] = iteration

    if own_provider:
        provider.shutdown()

    return results


# Keep backward-compatible alias
run_anthropic_sdk_agent = run_anthropic_agent


if __name__ == "__main__":
    from benchmarks.mocks import MockAnthropicClient

    client = MockAnthropicClient()
    result = run_anthropic_agent(mock_client=client)
    print(f"\nAnthropic SDK agent completed in {result['iterations']} iterations")
    print(f"Steps: {len(result['steps'])}")
    print(f"Final answer: {result.get('final_answer', 'N/A')[:80]}")
    stats = client.get_call_stats()
    print(f"API calls: {stats['call_count']}")
    print(f"Total tokens: {stats['total_input_tokens']} in, {stats['total_output_tokens']} out")
