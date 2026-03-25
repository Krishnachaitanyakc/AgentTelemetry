"""Vanilla OTel agent -- standard OpenTelemetry, no agent-specific span kinds.

This is the baseline condition. It instruments the same research agent as the
custom_agent app, but uses plain ``tracer.start_as_current_span()`` instead of
``start_agent_span()``.  Spans carry generic attributes (llm.model, tool.name,
etc.) but never set ``agenttelemetry.span.kind``.

The purpose is to measure what fraction of faults can be detected with
off-the-shelf OTel instrumentation vs. agent-aware telemetry.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

from opentelemetry import trace
from opentelemetry.trace import StatusCode

# Re-use the same path setup as the custom agent
_BENCHMARKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = os.path.dirname(_BENCHMARKS_DIR)
_SRC_DIR = os.path.join(_ROOT_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from agenttelemetry import AgentTelemetryProvider
from agenttelemetry.core.spans import estimate_cost

# Re-use mock tools from the custom agent
from benchmarks.apps.custom_agent.app import AVAILABLE_TOOLS, _execute_tool


def run_vanilla_agent(
    task: str = "Research the latest developments in quantum computing",
    mock_client: Any = None,
    provider: Optional[AgentTelemetryProvider] = None,
    model: str = "claude-sonnet-4",
    max_iterations: int = 5,
    fault_injector: Any = None,
) -> Dict[str, Any]:
    """Run a research agent with vanilla OTel instrumentation (no agent span kinds).

    Same logic as ``run_custom_agent`` but uses plain OTel spans.  No
    ``agenttelemetry.span.kind`` attribute is set on any span.

    Note: fault_injector is accepted but ignored -- vanilla OTel cannot
    detect span-attribute faults because it lacks agent-specific span kinds.
    """
    tracer = provider.get_tracer("vanilla-otel") if provider else trace.get_tracer("vanilla-otel")

    results: Dict[str, Any] = {"steps": [], "final_answer": None, "iterations": 0}

    with tracer.start_as_current_span("research-task", attributes={
        "agent.name": "researcher",
        "agent.framework": "vanilla_otel",
        "agent.task": task,
    }):

        # 1. Planning step
        with tracer.start_as_current_span("plan", attributes={
            "planning.strategy": "sequential",
        }):
            plan = ["search for information", "analyze results", "synthesize answer"]
            results["steps"].append({"type": "planning", "plan": plan})

        # 2. Memory check
        with tracer.start_as_current_span("check-memory"):
            results["steps"].append({"type": "memory_read", "found": False})

        # 3. Agent loop
        messages: List[Dict[str, Any]] = [{"role": "user", "content": task}]
        iteration = 0
        current_agent = "researcher"

        while iteration < max_iterations:
            iteration += 1

            # Reasoning step
            with tracer.start_as_current_span(f"reason-{iteration}"):
                results["steps"].append({"type": "reasoning", "iteration": iteration})

            # LLM call
            with tracer.start_as_current_span(f"llm-call-{iteration}", attributes={
                "llm.model": model,
                "llm.provider": "anthropic",
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
                        llm_span.set_status(StatusCode.ERROR, f"Timeout: {e}")
                        llm_span.record_exception(e)
                        llm_span.set_attribute("llm.input_tokens", 0)
                        llm_span.set_attribute("llm.output_tokens", 0)
                        results["steps"].append({"type": "llm_timeout", "error": str(e)})
                        break

                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    llm_span.set_attribute("llm.input_tokens", input_tokens)
                    llm_span.set_attribute("llm.output_tokens", output_tokens)
                    cost = estimate_cost(model, input_tokens, output_tokens)
                    llm_span.set_attribute("llm.cost", cost)

                    # Process response
                    has_tool_use = False
                    for block in response.content:
                        if block.type == "tool_use":
                            has_tool_use = True

                            if block.name == "delegate_task":
                                target_agent = block.input.get("agent", "unknown")
                                with tracer.start_as_current_span(
                                    f"delegate-{current_agent}-to-{target_agent}",
                                    attributes={
                                        "delegation.source_agent": current_agent,
                                        "delegation.target_agent": target_agent,
                                    },
                                ):
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
                            with tracer.start_as_current_span(
                                f"tool-{block.name}",
                                attributes={"tool.name": block.name},
                            ) as tool_span:
                                try:
                                    tool_result = _execute_tool(block.name, block.input)
                                    tool_span.set_attribute("tool.status", "success")
                                    tool_span.set_attribute("tool.latency_ms", (time.time() - tool_start) * 1000)
                                    results["steps"].append({
                                        "type": "tool_call",
                                        "tool": block.name,
                                        "status": "success",
                                    })
                                except Exception as e:
                                    tool_span.set_status(StatusCode.ERROR, str(e))
                                    tool_span.record_exception(e)
                                    tool_span.set_attribute("tool.status", "error")
                                    tool_span.set_attribute("tool.latency_ms", (time.time() - tool_start) * 1000)
                                    tool_result = {"error": str(e)}
                                    results["steps"].append({
                                        "type": "tool_call",
                                        "tool": block.name,
                                        "status": "error",
                                        "error": str(e),
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
                    llm_span.set_attribute("llm.input_tokens", 500)
                    llm_span.set_attribute("llm.output_tokens", 200)
                    results["final_answer"] = "Demo response without mock client."
                    break

        results["iterations"] = iteration

        # 4. Guard rail check
        with tracer.start_as_current_span("content-safety"):
            results["steps"].append({"type": "guardrail", "result": "pass"})

        # 5. Store to memory
        with tracer.start_as_current_span("store-memory"):
            results["steps"].append({"type": "memory_write"})

    return results
