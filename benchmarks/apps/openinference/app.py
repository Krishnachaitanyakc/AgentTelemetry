"""OpenInference (Arize) semantic conventions agent.

Instruments the same research agent using the OpenInference span-kind taxonomy
defined by Arize AI (https://github.com/Arize-ai/openinference). OpenInference
defines ten typed span kinds; this app exercises six of them as they apply to
our research-agent workload:

  - AGENT      -- root agent lifecycle
  - LLM        -- model invocation
  - TOOL       -- tool execution
  - CHAIN      -- planning / reasoning step (the OpenInference "intermediate
                  step" kind covers both)
  - RETRIEVER  -- RAG fetch
  - GUARDRAIL  -- safety / policy check

Detectable faults (6 of 14): wrong_tool, infinite_loop, tool_failure, timeout,
context_overflow, cost_explosion.

NOT detectable (8 of 14): hallucination (RETRIEVER span carries no
output-grounding signal), circular_delegation (no typed delegation source/
target identifiers), stale_retrieval (no staleness attribute), guardrail_bypass
(GUARDRAIL kind exists but no constrained pass/fail/warn outcome attribute),
planning_failure (CHAIN is undifferentiated planning vs reasoning),
reasoning_loop (same), agent_misroute (no inter-agent topology),
memory_corruption (no memory kind).
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

from opentelemetry import trace
from opentelemetry.trace import StatusCode, SpanKind

# Re-use the same path setup as the custom agent
_BENCHMARKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = os.path.dirname(_BENCHMARKS_DIR)
_SRC_DIR = os.path.join(_ROOT_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from agenttelemetry import AgentTelemetryProvider

# Re-use mock tools from the custom agent
from benchmarks.apps.custom_agent.app import AVAILABLE_TOOLS, _execute_tool

# ---------------------------------------------------------------------------
# OpenInference attribute keys
# (from https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md)
# ---------------------------------------------------------------------------
OI_SPAN_KIND = "openinference.span.kind"
OI_INPUT_VALUE = "input.value"
OI_OUTPUT_VALUE = "output.value"
OI_LLM_MODEL_NAME = "llm.model_name"
OI_LLM_TOKEN_COUNT_PROMPT = "llm.token_count.prompt"
OI_LLM_TOKEN_COUNT_COMPLETION = "llm.token_count.completion"
OI_TOOL_NAME = "tool.name"
OI_TOOL_PARAMETERS = "tool.parameters"
OI_RETRIEVAL_DOCUMENTS = "retrieval.documents"


def run_openinference_agent(
    task: str = "Research the latest developments in quantum computing",
    mock_client: Any = None,
    provider: Optional[AgentTelemetryProvider] = None,
    model: str = "claude-sonnet-4",
    max_iterations: int = 5,
    fault_injector: Any = None,
) -> Dict[str, Any]:
    """Run the research agent with OpenInference semantic-convention instrumentation."""
    tracer = provider.get_tracer("openinference") if provider else trace.get_tracer("openinference")

    results: Dict[str, Any] = {"steps": [], "final_answer": None, "iterations": 0}

    # Root: AGENT span
    with tracer.start_as_current_span(
        "researcher",
        kind=SpanKind.INTERNAL,
        attributes={
            OI_SPAN_KIND: "AGENT",
            "agent.name": "researcher",
            "agent.framework": "openinference",
            OI_INPUT_VALUE: task,
        },
    ):
        # 1. Planning -- CHAIN span (OpenInference does not differentiate
        #    planning vs reasoning; both go under CHAIN).
        with tracer.start_as_current_span(
            "plan",
            attributes={OI_SPAN_KIND: "CHAIN"},
        ):
            plan = ["search for information", "analyze results", "synthesize answer"]
            results["steps"].append({"type": "planning", "plan": plan})

        # 2. Memory check -- OpenInference has no memory kind. Generic span.
        with tracer.start_as_current_span("check-memory"):
            results["steps"].append({"type": "memory_read", "found": False})

        # 2b. Retrieval -- RETRIEVER span
        with tracer.start_as_current_span(
            "retrieve-context",
            kind=SpanKind.CLIENT,
            attributes={
                OI_SPAN_KIND: "RETRIEVER",
                "retrieval.source": "knowledge_base_v1",
            },
        ):
            results["steps"].append({"type": "retrieval", "source": "knowledge_base_v1"})

        # 3. Agent loop
        messages: List[Dict[str, Any]] = [{"role": "user", "content": task}]
        iteration = 0
        current_agent = "researcher"

        while iteration < max_iterations:
            iteration += 1

            # Reasoning step -- CHAIN (same kind as planning)
            with tracer.start_as_current_span(
                f"reason-{iteration}",
                attributes={OI_SPAN_KIND: "CHAIN"},
            ):
                results["steps"].append({"type": "reasoning", "iteration": iteration})

            # LLM call -- LLM span
            with tracer.start_as_current_span(
                f"llm {model}",
                kind=SpanKind.CLIENT,
                attributes={
                    OI_SPAN_KIND: "LLM",
                    OI_LLM_MODEL_NAME: model,
                },
            ) as llm_span:
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
                        llm_span.set_attribute(OI_LLM_TOKEN_COUNT_PROMPT, 0)
                        llm_span.set_attribute(OI_LLM_TOKEN_COUNT_COMPLETION, 0)
                        results["steps"].append({"type": "llm_timeout", "error": str(e)})
                        break

                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    llm_span.set_attribute(OI_LLM_TOKEN_COUNT_PROMPT, input_tokens)
                    llm_span.set_attribute(OI_LLM_TOKEN_COUNT_COMPLETION, output_tokens)

                    has_tool_use = False
                    for block in response.content:
                        if block.type == "tool_use":
                            has_tool_use = True

                            if block.name == "delegate_task":
                                # OpenInference AGENT kind exists but lacks
                                # typed source/target identifiers, so we wrap
                                # the delegation as a generic AGENT child span
                                # with free-form attributes.
                                target_agent = block.input.get("agent", "unknown")
                                with tracer.start_as_current_span(
                                    f"agent {target_agent}",
                                    kind=SpanKind.INTERNAL,
                                    attributes={
                                        OI_SPAN_KIND: "AGENT",
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

                            # TOOL span
                            tool_start = time.time()
                            with tracer.start_as_current_span(
                                f"tool {block.name}",
                                kind=SpanKind.INTERNAL,
                                attributes={
                                    OI_SPAN_KIND: "TOOL",
                                    OI_TOOL_NAME: block.name,
                                },
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
                    llm_span.set_attribute(OI_LLM_TOKEN_COUNT_PROMPT, 500)
                    llm_span.set_attribute(OI_LLM_TOKEN_COUNT_COMPLETION, 200)
                    results["final_answer"] = "Demo response without mock client."
                    break

        results["iterations"] = iteration

        # 4. Guardrail -- GUARDRAIL span (free-form attribute, no constrained outcome)
        with tracer.start_as_current_span(
            "content-safety",
            attributes={OI_SPAN_KIND: "GUARDRAIL"},
        ):
            results["steps"].append({"type": "guardrail", "result": "pass"})

        # 5. Memory write -- no OpenInference kind
        with tracer.start_as_current_span("store-memory"):
            results["steps"].append({"type": "memory_write"})

    return results
