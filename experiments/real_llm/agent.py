"""ReAct agent for real LLM experiment.

Provider-agnostic agent loop that produces full AgentTelemetry trace trees:
AGENT -> PLANNING -> MEMORY(read) -> [REASONING -> LLM_CALL -> tool spans]* -> MEMORY(write)
"""

from __future__ import annotations

import json
import time
import traceback
from typing import Any, Dict, List, Optional

from opentelemetry.trace import StatusCode

from agenttelemetry.core.spans import (
    AGENT_FRAMEWORK,
    AGENT_NAME,
    AGENT_SPAN_KIND,
    AGENT_TASK,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_LATENCY_MS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    LLM_PROMPT,
    LLM_COMPLETION,
    LLM_PROVIDER,
    LLM_TOTAL_TOKENS,
    MEMORY_KEY,
    MEMORY_OPERATION,
    PLANNING_STEP_COUNT,
    PLANNING_STRATEGY,
    REASONING_CHAIN,
    AgentSpanKind,
    estimate_cost,
    start_agent_span,
)

from experiments.real_llm.config import (
    BudgetTracker,
    ModelConfig,
    UnifiedResponse,
)
from experiments.real_llm.tools import execute_tool, get_tool_definitions

# System prompt for the ReAct agent
SYSTEM_PROMPT = """You are a research assistant that answers questions using available tools.

IMPORTANT RULES:
1. Always use tools to look up factual information - never guess or rely on your training data.
2. Use the calculator for any arithmetic - never do mental math.
3. When the question asks you to verify an answer, you MUST use the verify_answer tool.
4. Think step by step and use the appropriate tools in sequence.
5. After getting tool results, provide a final numerical answer.

Available tools will be provided via function calling."""

MAX_ITERATIONS = 8


def call_llm(
    client: Any,
    config: ModelConfig,
    messages: List[Dict[str, Any]],
    tools: list,
    tracer=None,
    budget: Optional[BudgetTracker] = None,
) -> UnifiedResponse:
    """Make an LLM API call with retries and telemetry.

    Returns a UnifiedResponse. Records an LLM_CALL span.
    """
    last_error = None

    for attempt in range(3):
        try:
            start_time = time.time()

            if config.provider == "openai":
                kwargs = {
                    "model": config.model_id,
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools
                if config.is_reasoning:
                    kwargs["max_completion_tokens"] = config.max_output_tokens
                else:
                    kwargs["max_tokens"] = config.max_output_tokens

                raw_response = client.chat.completions.create(**kwargs)
                response = UnifiedResponse.from_openai(raw_response)

            elif config.provider == "anthropic":
                # Separate system message from conversation
                system_msg = ""
                conv_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_msg = msg["content"]
                    else:
                        conv_messages.append(msg)

                kwargs = {
                    "model": config.model_id,
                    "messages": conv_messages,
                    "max_tokens": config.max_output_tokens,
                }
                if system_msg:
                    kwargs["system"] = system_msg
                if tools:
                    kwargs["tools"] = tools

                raw_response = client.messages.create(**kwargs)
                response = UnifiedResponse.from_anthropic(raw_response)

            latency_ms = (time.time() - start_time) * 1000

            # Record cost
            cost = 0.0
            if budget:
                cost = budget.record(
                    config.model_id,
                    response.input_tokens,
                    response.output_tokens,
                    config,
                )
            else:
                cost = estimate_cost(config.model_id, response.input_tokens, response.output_tokens)

            # Record LLM_CALL span
            span_attrs = {
                LLM_MODEL: config.model_id,
                LLM_PROVIDER: config.provider,
                LLM_INPUT_TOKENS: response.input_tokens,
                LLM_OUTPUT_TOKENS: response.output_tokens,
                LLM_TOTAL_TOKENS: response.input_tokens + response.output_tokens,
                LLM_COST: cost,
                LLM_LATENCY_MS: latency_ms,
            }
            if response.reasoning_tokens > 0:
                span_attrs["llm.reasoning_tokens"] = response.reasoning_tokens

            with start_agent_span(
                name=f"llm_call({config.display_name})",
                kind=AgentSpanKind.LLM_CALL,
                tracer=tracer,
                attributes=span_attrs,
            ):
                pass

            return response

        except Exception as e:
            last_error = e
            error_str = str(e)
            # Retry on rate limits
            if "rate" in error_str.lower() or "429" in error_str:
                wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                time.sleep(wait_time)
                continue
            # Don't retry on other errors
            raise

    raise last_error


def run_agent(
    client: Any,
    config: ModelConfig,
    question: str,
    tracer=None,
    budget: Optional[BudgetTracker] = None,
    system_prompt: Optional[str] = None,
    exclude_tools: Optional[List[str]] = None,
    extra_messages: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run the ReAct agent on a single question.

    Returns a dict with: answer, tool_calls_made, iterations, total_tokens, cost, error
    """
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT

    tools = get_tool_definitions(config.provider, exclude_tools=exclude_tools)

    result = {
        "answer": "",
        "tool_calls_made": [],
        "iterations": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "cost": 0.0,
        "error": None,
    }

    with start_agent_span(
        name=f"agent({config.display_name})",
        kind=AgentSpanKind.AGENT,
        tracer=tracer,
        attributes={
            AGENT_NAME: "research_assistant",
            AGENT_FRAMEWORK: "agenttelemetry_experiment",
            AGENT_TASK: question[:200],
        },
    ):
        # PLANNING span
        with start_agent_span(
            name="planning",
            kind=AgentSpanKind.PLANNING,
            tracer=tracer,
            attributes={
                PLANNING_STRATEGY: "react_loop",
                PLANNING_STEP_COUNT: MAX_ITERATIONS,
            },
        ):
            pass

        # MEMORY span (read context)
        with start_agent_span(
            name="memory_read",
            kind=AgentSpanKind.MEMORY,
            tracer=tracer,
            attributes={
                MEMORY_OPERATION: "read",
                MEMORY_KEY: "conversation_history",
            },
        ):
            pass

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        if extra_messages:
            messages.extend(extra_messages)

        try:
            for iteration in range(MAX_ITERATIONS):
                result["iterations"] = iteration + 1

                # REASONING span
                with start_agent_span(
                    name=f"reasoning_step_{iteration + 1}",
                    kind=AgentSpanKind.REASONING,
                    tracer=tracer,
                    attributes={
                        REASONING_CHAIN: f"Step {iteration + 1}: Analyzing question and determining next action",
                    },
                ):
                    pass

                # LLM call
                response = call_llm(
                    client, config, messages, tools,
                    tracer=tracer, budget=budget,
                )

                result["total_input_tokens"] += response.input_tokens
                result["total_output_tokens"] += response.output_tokens
                result["cost"] += estimate_cost(
                    config.model_id, response.input_tokens, response.output_tokens
                )

                # Check if the model wants to call tools
                if not response.tool_calls:
                    # Model is done — extract final answer
                    result["answer"] = response.content
                    break

                # Process tool calls
                if config.provider == "openai":
                    # Append assistant message with tool calls
                    assistant_msg = {"role": "assistant", "content": response.content or None}
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                    messages.append(assistant_msg)

                    for tc in response.tool_calls:
                        tool_result = execute_tool(tc["name"], tc["arguments"], tracer=tracer)
                        result["tool_calls_made"].append(tc["name"])

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result,
                        })

                elif config.provider == "anthropic":
                    # Append assistant message
                    content_blocks = []
                    if response.content:
                        content_blocks.append({"type": "text", "text": response.content})
                    for tc in response.tool_calls:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["arguments"],
                        })
                    messages.append({"role": "assistant", "content": content_blocks})

                    # Tool results
                    tool_result_blocks = []
                    for tc in response.tool_calls:
                        tool_result = execute_tool(tc["name"], tc["arguments"], tracer=tracer)
                        result["tool_calls_made"].append(tc["name"])

                        tool_result_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": tc["id"],
                            "content": tool_result,
                        })
                    messages.append({"role": "user", "content": tool_result_blocks})

            else:
                # Max iterations reached
                result["answer"] = response.content if response else ""
                result["error"] = "max_iterations_reached"

        except Exception as e:
            result["error"] = str(e)
            result["answer"] = ""

        # MEMORY span (write)
        with start_agent_span(
            name="memory_write",
            kind=AgentSpanKind.MEMORY,
            tracer=tracer,
            attributes={
                MEMORY_OPERATION: "write",
                MEMORY_KEY: "agent_result",
            },
        ):
            pass

    return result
