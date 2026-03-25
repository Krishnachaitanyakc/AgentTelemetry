"""Custom agent using manual AgentTelemetry instrumentation.

This reference application demonstrates direct use of the AgentTelemetry API
without any framework adapter. It creates a simple research agent that:
1. Plans a research task
2. Makes LLM calls for generation
3. Uses tools for information retrieval
4. Demonstrates all span kinds
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure src and root are importable
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
    AGENT_MISROUTED, AGENT_EXPECTED_NAME,
    LLM_MODEL, LLM_PROVIDER, LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS, LLM_COST,
    TOOL_NAME, TOOL_INPUT, TOOL_OUTPUT, TOOL_STATUS, TOOL_LATENCY_MS,
    PLANNING_STRATEGY, PLANNING_STEP_COUNT,
    DELEGATION_SOURCE_AGENT, DELEGATION_TARGET_AGENT,
    MEMORY_OPERATION, MEMORY_KEY, MEMORY_CORRUPTED,
    GUARDRAIL_NAME, GUARDRAIL_RESULT,
    REASONING_CHAIN,
    RETRIEVAL_SOURCE, RETRIEVAL_STALENESS_SECONDS,
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
        "name": "file_reader",
        "description": "Read contents of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
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
        "file_reader": {"content": "File contents here", "lines": 5},
    }
    return results.get(tool_name, {"status": "ok"})


# -- Agent logic --------------------------------------------------------------

def run_custom_agent(
    task: str = "Research the latest developments in quantum computing",
    mock_client: Any = None,
    provider: Optional[AgentTelemetryProvider] = None,
    model: str = "claude-sonnet-4",
    max_iterations: int = 5,
    fault_injector: Any = None,
) -> Dict[str, Any]:
    """Run a custom agent with full manual instrumentation.

    Args:
        task: The task for the agent to perform.
        mock_client: A MockAnthropicClient instance (required for benchmarks).
        provider: Pre-configured AgentTelemetryProvider, or creates one.
        model: Model name for LLM calls.
        max_iterations: Maximum agent loop iterations.
        fault_injector: Optional FaultInjector whose fault_type controls
            span-attribute fault injection (STALE_RETRIEVAL, GUARDRAIL_BYPASS,
            PLANNING_FAILURE, REASONING_LOOP, AGENT_MISROUTE, MEMORY_CORRUPTION).

    Returns:
        Dict with agent results and telemetry metadata.
    """
    own_provider = provider is None
    if own_provider:
        provider = configure(service_name="custom-agent", console=True)

    tracer = provider.get_tracer()
    results: Dict[str, Any] = {"steps": [], "final_answer": None, "iterations": 0}

    # Determine which span-attribute fault (if any) is active
    _active_fault = getattr(fault_injector, "fault_type", None)
    _ft_val = getattr(_active_fault, "value", None)

    with start_agent_span("research-task", AgentSpanKind.AGENT, tracer=tracer,
                          attributes={
                              AGENT_NAME: "researcher",
                              AGENT_FRAMEWORK: "custom",
                              AGENT_TASK: task,
                          }) as agent_span:

        # Inject AGENT_MISROUTE: mark the span as misrouted
        if _ft_val == "agent_misroute":
            agent_span.set_attribute(AGENT_MISROUTED, True)
            agent_span.set_attribute(AGENT_EXPECTED_NAME, "specialist")

        # 1. Planning step
        _plan_step_count = 15 if _ft_val == "planning_failure" else 3
        with start_agent_span("plan", AgentSpanKind.PLANNING, tracer=tracer,
                              attributes={
                                  PLANNING_STRATEGY: "sequential",
                                  PLANNING_STEP_COUNT: _plan_step_count,
                              }):
            plan = ["search for information", "analyze results", "synthesize answer"]
            results["steps"].append({"type": "planning", "plan": plan})

        # 2. Memory check
        with start_agent_span("check-memory", AgentSpanKind.MEMORY, tracer=tracer,
                              attributes={
                                  MEMORY_OPERATION: "read",
                                  MEMORY_KEY: "previous_research",
                              }) as mem_read_span:
            # Inject MEMORY_CORRUPTION on the read span
            if _ft_val == "memory_corruption":
                mem_read_span.set_attribute(MEMORY_CORRUPTED, True)
            results["steps"].append({"type": "memory_read", "found": False})

        # 2b. Retrieval step (present when STALE_RETRIEVAL fault exercises the RETRIEVAL span kind)
        if _ft_val == "stale_retrieval":
            with start_agent_span("retrieve-context", AgentSpanKind.RETRIEVAL, tracer=tracer,
                                  attributes={
                                      RETRIEVAL_SOURCE: "stale_cache",
                                      RETRIEVAL_STALENESS_SECONDS: 7200,
                                  }):
                results["steps"].append({"type": "retrieval", "staleness_seconds": 7200})

        # 3. Agent loop: LLM call -> maybe tool -> repeat
        messages = [{"role": "user", "content": task}]
        iteration = 0
        current_agent = "researcher"  # Track current agent for delegation cycles

        while iteration < max_iterations:
            iteration += 1

            # Reasoning step
            _reasoning_chain = "stuck-in-loop" if _ft_val == "reasoning_loop" else f"step-{iteration}"
            with start_agent_span(f"reason-{iteration}", AgentSpanKind.REASONING, tracer=tracer,
                                  attributes={REASONING_CHAIN: _reasoning_chain}):
                results["steps"].append({"type": "reasoning", "iteration": iteration})

            # LLM call
            llm_start = time.time()
            with start_agent_span(f"llm-call-{iteration}", AgentSpanKind.LLM_CALL, tracer=tracer,
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

                    # Process response
                    has_tool_use = False
                    for block in response.content:
                        if block.type == "tool_use":
                            has_tool_use = True

                            # Special handling: delegate_task creates a DELEGATION span
                            if block.name == "delegate_task":
                                target_agent = block.input.get("agent", "unknown")
                                # Track delegation: source is the current_agent, target is the delegated agent.
                                # After delegation, the target becomes the current agent (simulating handoff).
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
                                # Add tool result to messages
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
                                        "type": "tool_call",
                                        "tool": block.name,
                                        "status": "success",
                                    })
                                except Exception as e:
                                    tool_span.set_attribute(TOOL_STATUS, "error")
                                    tool_span.set_attribute(TOOL_LATENCY_MS, (time.time() - tool_start) * 1000)
                                    tool_result = {"error": str(e)}
                                    results["steps"].append({
                                        "type": "tool_call",
                                        "tool": block.name,
                                        "status": "error",
                                        "error": str(e),
                                    })

                            # Add tool result to messages for next iteration
                            messages.append({"role": "assistant", "content": response.content})
                            messages.append({
                                "role": "user",
                                "content": [{"type": "tool_result", "tool_use_id": block.id, "content": str(tool_result)}],
                            })

                    if not has_tool_use:
                        # Text response, agent is done
                        final_text = response.content[0].text if response.content else ""
                        results["final_answer"] = final_text
                        results["steps"].append({"type": "final_answer", "text": final_text[:100]})
                        break
                else:
                    # No mock client, just demonstrate spans
                    llm_span.set_attribute(LLM_INPUT_TOKENS, 500)
                    llm_span.set_attribute(LLM_OUTPUT_TOKENS, 200)
                    results["final_answer"] = "Demo response without mock client."
                    break

        results["iterations"] = iteration

        # 4. Guard rail check
        _guardrail_result = "bypass" if _ft_val == "guardrail_bypass" else "pass"
        with start_agent_span("content-safety", AgentSpanKind.GUARD_RAIL, tracer=tracer,
                              attributes={
                                  GUARDRAIL_NAME: "content_safety",
                                  GUARDRAIL_RESULT: _guardrail_result,
                              }):
            results["steps"].append({"type": "guardrail", "result": _guardrail_result})

        # 5. Store to memory
        with start_agent_span("store-memory", AgentSpanKind.MEMORY, tracer=tracer,
                              attributes={
                                  MEMORY_OPERATION: "write",
                                  MEMORY_KEY: "research_result",
                              }):
            results["steps"].append({"type": "memory_write"})

    if own_provider:
        provider.shutdown()

    return results


if __name__ == "__main__":
    from benchmarks.mocks import MockAnthropicClient

    client = MockAnthropicClient()
    result = run_custom_agent(mock_client=client)
    print(f"\nAgent completed in {result['iterations']} iterations")
    print(f"Steps: {len(result['steps'])}")
    print(f"Final answer: {result.get('final_answer', 'N/A')[:80]}")
    stats = client.get_call_stats()
    print(f"API calls: {stats['call_count']}")
    print(f"Total tokens: {stats['total_input_tokens']} in, {stats['total_output_tokens']} out")
