"""CrewAI multi-agent team using manual AgentTelemetry instrumentation.

Simulates a CrewAI Crew with 3 agents (researcher, writer, reviewer):
1. AGENT span per crew member
2. DELEGATION spans between crew members (sequential handoff)
3. LLM_CALL spans for each agent's thinking
4. TOOL_CALL spans for research tools
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
    AGENT_NAME, AGENT_FRAMEWORK, AGENT_TASK, AGENT_ROLE,
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

# CrewAI crew definition: sequential pipeline
_CREW_AGENTS = [
    {"name": "researcher", "role": "research_analyst", "goal": "Find relevant information"},
    {"name": "writer", "role": "content_writer", "goal": "Write clear content from research"},
    {"name": "reviewer", "role": "quality_reviewer", "goal": "Review and refine the output"},
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


def _run_crew_member(
    agent_def: Dict[str, str],
    task: str,
    context: str,
    mock_client: Any,
    tracer: Any,
    model: str,
    max_iterations: int,
    results: Dict[str, Any],
    current_agent: str,
) -> tuple:
    """Run a single crew member agent, returning (output_text, current_agent)."""
    agent_name = agent_def["name"]

    with start_agent_span(f"crew-{agent_name}", AgentSpanKind.AGENT, tracer=tracer,
                          attributes={
                              AGENT_NAME: agent_name,
                              AGENT_FRAMEWORK: "crewai",
                              AGENT_ROLE: agent_def["role"],
                              AGENT_TASK: f"{agent_def['goal']}: {task}",
                          }):

        messages = [
            {"role": "user", "content": f"Context: {context}\n\nTask: {task}\nGoal: {agent_def['goal']}"},
        ]
        iteration = 0
        output_text = ""

        while iteration < max_iterations:
            iteration += 1

            with start_agent_span(f"{agent_name}-llm-{iteration}", AgentSpanKind.LLM_CALL, tracer=tracer,
                                  attributes={
                                      LLM_MODEL: model,
                                      LLM_PROVIDER: "openai",
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
                        results["steps"].append({"type": "llm_timeout", "agent": agent_name, "error": str(e)})
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

                            tool_start = time.time()
                            with start_agent_span(f"tool-{block.name}", AgentSpanKind.TOOL_CALL, tracer=tracer,
                                                  attributes={TOOL_NAME: block.name}) as tool_span:
                                try:
                                    tool_result = _execute_tool(block.name, block.input)
                                    tool_span.set_attribute(TOOL_STATUS, "success")
                                    tool_span.set_attribute(TOOL_LATENCY_MS, (time.time() - tool_start) * 1000)
                                    results["steps"].append({
                                        "type": "tool_call", "agent": agent_name,
                                        "tool": block.name, "status": "success",
                                    })
                                except Exception as e:
                                    tool_span.set_attribute(TOOL_STATUS, "error")
                                    tool_span.set_attribute(TOOL_LATENCY_MS, (time.time() - tool_start) * 1000)
                                    tool_result = {"error": str(e)}
                                    results["steps"].append({
                                        "type": "tool_call", "agent": agent_name,
                                        "tool": block.name, "status": "error", "error": str(e),
                                    })

                            messages.append({"role": "assistant", "content": response.content})
                            messages.append({
                                "role": "user",
                                "content": [{"type": "tool_result", "tool_use_id": block.id,
                                             "content": str(tool_result)}],
                            })

                    if not has_tool_use:
                        output_text = response.content[0].text if response.content else ""
                        results["steps"].append({
                            "type": "agent_output", "agent": agent_name, "text": output_text[:100],
                        })
                        break
                else:
                    llm_span.set_attribute(LLM_INPUT_TOKENS, 500)
                    llm_span.set_attribute(LLM_OUTPUT_TOKENS, 200)
                    output_text = f"Demo output from {agent_name}."
                    break

        results["iterations"] += iteration

    return output_text, current_agent


# -- Agent logic --------------------------------------------------------------

def run_crewai_agent(
    task: str = "Research and write a report on AI trends",
    mock_client: Any = None,
    provider: Optional[AgentTelemetryProvider] = None,
    model: str = "gpt-4o",
    max_iterations: int = 5,
    fault_injector: Any = None,
) -> Dict[str, Any]:
    """Run a CrewAI-style multi-agent team with manual instrumentation.

    Simulates CrewAI's sequential crew pattern:
    crew(AGENT) -> researcher(AGENT+LLM) -delegate-> writer(AGENT+LLM) -delegate-> reviewer(AGENT+LLM)

    Args:
        task: The task for the crew to perform.
        mock_client: A MockAnthropicClient or MockOpenAIClient instance.
        provider: Pre-configured AgentTelemetryProvider, or creates one.
        model: Model name for LLM calls.
        max_iterations: Maximum iterations per crew member.

    Returns:
        Dict with agent results and telemetry metadata.
    """
    own_provider = provider is None
    if own_provider:
        provider = configure(service_name="crewai-team", console=True)

    tracer = provider.get_tracer()
    results: Dict[str, Any] = {"steps": [], "final_answer": None, "iterations": 0}

    # Top-level crew span
    with start_agent_span("crewai-crew", AgentSpanKind.AGENT, tracer=tracer,
                          attributes={
                              AGENT_NAME: "research-crew",
                              AGENT_FRAMEWORK: "crewai",
                              AGENT_TASK: task,
                          }):

        context = ""
        current_agent = "research-crew"

        for i, agent_def in enumerate(_CREW_AGENTS):
            # Create delegation span for handoff between crew members
            if i > 0:
                prev_agent = _CREW_AGENTS[i - 1]["name"]
                with start_agent_span(f"delegate-{prev_agent}-to-{agent_def['name']}",
                                      AgentSpanKind.DELEGATION, tracer=tracer,
                                      attributes={
                                          DELEGATION_SOURCE_AGENT: prev_agent,
                                          DELEGATION_TARGET_AGENT: agent_def["name"],
                                      }):
                    results["steps"].append({
                        "type": "delegation",
                        "source": prev_agent,
                        "target": agent_def["name"],
                    })
                current_agent = agent_def["name"]

            output_text, current_agent = _run_crew_member(
                agent_def=agent_def,
                task=task,
                context=context,
                mock_client=mock_client,
                tracer=tracer,
                model=model,
                max_iterations=max_iterations,
                results=results,
                current_agent=current_agent,
            )
            context = output_text  # Pass output as context to next agent

        results["final_answer"] = context

    if own_provider:
        provider.shutdown()

    return results


# Keep backward-compatible alias
run_crewai_team_agent = run_crewai_agent


if __name__ == "__main__":
    from benchmarks.mocks import MockAnthropicClient

    client = MockAnthropicClient()
    result = run_crewai_agent(mock_client=client)
    print(f"\nCrewAI team completed in {result['iterations']} iterations")
    print(f"Steps: {len(result['steps'])}")
    print(f"Final answer: {result.get('final_answer', 'N/A')[:80]}")
    stats = client.get_call_stats()
    print(f"API calls: {stats['call_count']}")
    print(f"Total tokens: {stats['total_input_tokens']} in, {stats['total_output_tokens']} out")
