"""LlamaIndex query engine agent using manual AgentTelemetry instrumentation.

Simulates a LlamaIndex ReActAgent with query engine:
1. AGENT span (query engine orchestrator)
2. PLANNING span (sub-question decomposition)
3. RETRIEVAL span (index retrieval)
4. LLM_CALL span (synthesis / response generation)
5. TOOL_CALL spans if tools are used
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
    PLANNING_STRATEGY, PLANNING_STEP_COUNT,
    DELEGATION_SOURCE_AGENT, DELEGATION_TARGET_AGENT,
    RETRIEVAL_SOURCE, RETRIEVAL_QUERY, RETRIEVAL_DOC_COUNT,
    REASONING_CHAIN,
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

_MOCK_INDEX_NODES = [
    {"node_id": "node_1", "text": "LlamaIndex supports multiple index types...", "score": 0.92},
    {"node_id": "node_2", "text": "Vector stores enable semantic retrieval...", "score": 0.87},
    {"node_id": "node_3", "text": "Query engines orchestrate retrieval and synthesis...", "score": 0.81},
]

_SUB_QUESTIONS = [
    "What are the key concepts?",
    "What are the recent developments?",
    "How do these relate to the original question?",
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

def run_llamaindex_agent(
    task: str = "Query the knowledge base for relevant information",
    mock_client: Any = None,
    provider: Optional[AgentTelemetryProvider] = None,
    model: str = "gpt-4o",
    max_iterations: int = 5,
    fault_injector: Any = None,
) -> Dict[str, Any]:
    """Run a LlamaIndex-style query engine agent with manual instrumentation.

    Simulates the LlamaIndex SubQuestionQueryEngine + ReActAgent pattern:
    query(AGENT) -> decompose(PLANNING) -> retrieve(RETRIEVAL) -> synthesize(LLM_CALL) -> tool loop

    Args:
        task: The query for the knowledge base.
        mock_client: A MockAnthropicClient or MockOpenAIClient instance.
        provider: Pre-configured AgentTelemetryProvider, or creates one.
        model: Model name for LLM calls.
        max_iterations: Maximum agent loop iterations.

    Returns:
        Dict with agent results and telemetry metadata.
    """
    own_provider = provider is None
    if own_provider:
        provider = configure(service_name="llamaindex-agent", console=True)

    tracer = provider.get_tracer()
    results: Dict[str, Any] = {"steps": [], "final_answer": None, "iterations": 0}

    # Top-level query engine span
    with start_agent_span("llamaindex-query-engine", AgentSpanKind.AGENT, tracer=tracer,
                          attributes={
                              AGENT_NAME: "react-query-engine",
                              AGENT_FRAMEWORK: "llamaindex",
                              AGENT_TASK: task,
                          }):

        # 1. Sub-question decomposition (planning)
        with start_agent_span("sub-question-decomposition", AgentSpanKind.PLANNING, tracer=tracer,
                              attributes={
                                  PLANNING_STRATEGY: "sub_question",
                                  PLANNING_STEP_COUNT: len(_SUB_QUESTIONS),
                              }):
            results["steps"].append({
                "type": "planning",
                "strategy": "sub_question",
                "sub_questions": _SUB_QUESTIONS,
            })

        # 2. Index retrieval for each sub-question
        all_retrieved_text = []
        for i, sub_q in enumerate(_SUB_QUESTIONS):
            with start_agent_span(f"index-retrieval-{i+1}", AgentSpanKind.RETRIEVAL, tracer=tracer,
                                  attributes={
                                      RETRIEVAL_SOURCE: "vector_index",
                                      RETRIEVAL_QUERY: sub_q,
                                      RETRIEVAL_DOC_COUNT: len(_MOCK_INDEX_NODES),
                                  }):
                retrieved_text = " ".join(node["text"] for node in _MOCK_INDEX_NODES)
                all_retrieved_text.append(retrieved_text)
                results["steps"].append({
                    "type": "retrieval",
                    "sub_question": sub_q,
                    "node_count": len(_MOCK_INDEX_NODES),
                })

        # 3. ReAct agent loop: reasoning -> LLM synthesis -> maybe tool -> repeat
        context = " ".join(all_retrieved_text)
        messages = [
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {task}"},
        ]
        iteration = 0
        current_agent = "react-query-engine"

        while iteration < max_iterations:
            iteration += 1

            # Reasoning step (ReAct thought)
            with start_agent_span(f"react-thought-{iteration}", AgentSpanKind.REASONING, tracer=tracer,
                                  attributes={
                                      REASONING_CHAIN: f"thought-{iteration}: analyzing retrieved context",
                                  }):
                results["steps"].append({"type": "reasoning", "iteration": iteration})

            # LLM synthesis call
            with start_agent_span(f"llm-synthesize-{iteration}", AgentSpanKind.LLM_CALL, tracer=tracer,
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


if __name__ == "__main__":
    from benchmarks.mocks import MockAnthropicClient

    client = MockAnthropicClient()
    result = run_llamaindex_agent(mock_client=client)
    print(f"\nLlamaIndex agent completed in {result['iterations']} iterations")
    print(f"Steps: {len(result['steps'])}")
    print(f"Final answer: {result.get('final_answer', 'N/A')[:80]}")
    stats = client.get_call_stats()
    print(f"API calls: {stats['call_count']}")
    print(f"Total tokens: {stats['total_input_tokens']} in, {stats['total_output_tokens']} out")
