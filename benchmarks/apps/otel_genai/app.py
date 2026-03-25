"""OTel + GenAI semantic conventions agent -- uses the 4 OTel GenAI span types.

This is the intermediate baseline between vanilla_otel (no agent semantics) and
agenttelemetry (9 agent-specific span kinds).  It instruments the same research
agent using the OTel GenAI semantic conventions:

  1. Inference  (CLIENT span) -- gen_ai.operation.name = "chat"
  2. Embeddings (CLIENT span) -- gen_ai.operation.name = "embeddings"
  3. Retrievals (CLIENT span) -- gen_ai.operation.name = "retrieve", gen_ai.data_source.id
  4. Execute Tool (INTERNAL span) -- gen_ai.tool.name

The purpose is to measure what fraction of faults can be detected with
OTel + GenAI semantic conventions, which already provide structured LLM and
tool attributes, vs. the full agent-specific span kinds in AgentTelemetry.

Detectable faults (6 of 14):
  - wrong_tool       (via gen_ai.tool.name)
  - infinite_loop    (via repeated gen_ai.tool.name)
  - tool_failure     (via OTel ERROR status on Execute Tool span)
  - timeout          (via OTel ERROR status)
  - context_overflow (via gen_ai.usage.input_tokens growth)
  - cost_explosion   (via gen_ai.usage tokens + model pricing)

NOT detectable (8 of 14):
  - hallucination        (Retrievals span shows retrieval occurred, but no
                          grounding attribute to verify output fidelity)
  - circular_delegation  (no delegation span type)
  - stale_retrieval      (Retrievals span exists but no staleness attribute)
  - guardrail_bypass     (no guardrail span type)
  - planning_failure     (no planning span type)
  - reasoning_loop       (no reasoning span type)
  - agent_misroute       (no agent span type)
  - memory_corruption    (no memory span type)
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
from agenttelemetry.core.spans import estimate_cost

# Re-use mock tools from the custom agent
from benchmarks.apps.custom_agent.app import AVAILABLE_TOOLS, _execute_tool

# ---------------------------------------------------------------------------
# OTel GenAI Semantic Convention attribute keys
# (from https://opentelemetry.io/docs/specs/semconv/gen-ai/)
# ---------------------------------------------------------------------------
GENAI_OPERATION_NAME = "gen_ai.operation.name"
GENAI_REQUEST_MODEL = "gen_ai.request.model"
GENAI_RESPONSE_MODEL = "gen_ai.response.model"
GENAI_SYSTEM = "gen_ai.system"
GENAI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GENAI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GENAI_TOOL_NAME = "gen_ai.tool.name"
GENAI_TOOL_CALL_ID = "gen_ai.tool.call.id"
GENAI_DATA_SOURCE_ID = "gen_ai.data_source.id"


def run_otel_genai_agent(
    task: str = "Research the latest developments in quantum computing",
    mock_client: Any = None,
    provider: Optional[AgentTelemetryProvider] = None,
    model: str = "claude-sonnet-4",
    max_iterations: int = 5,
    fault_injector: Any = None,
) -> Dict[str, Any]:
    """Run a research agent with OTel GenAI semantic convention instrumentation.

    Uses the 4 GenAI span types (Inference, Embeddings, Retrievals, Execute Tool)
    but does NOT use any agenttelemetry-specific span kinds.

    The fault_injector parameter is accepted to match the custom_agent interface
    and to trigger span-attribute faults that this instrumentation may or may
    not be able to detect.
    """
    tracer = provider.get_tracer("otel-genai") if provider else trace.get_tracer("otel-genai")

    results: Dict[str, Any] = {"steps": [], "final_answer": None, "iterations": 0}

    _active_fault = getattr(fault_injector, "fault_type", None)
    _ft_val = getattr(_active_fault, "value", None)

    # Root span: not part of GenAI conventions, but needed to group the trace
    with tracer.start_as_current_span("research-task", attributes={
        "agent.name": "researcher",
        "agent.framework": "otel_genai",
        "agent.task": task,
    }):

        # 1. Planning step -- GenAI has no planning span type.
        # We still create a generic span for the operation.
        with tracer.start_as_current_span("plan", attributes={
            "planning.strategy": "sequential",
        }):
            plan = ["search for information", "analyze results", "synthesize answer"]
            results["steps"].append({"type": "planning", "plan": plan})

        # 2. Memory check -- GenAI has no memory span type.
        with tracer.start_as_current_span("check-memory"):
            results["steps"].append({"type": "memory_read", "found": False})

        # 2b. Retrieval step -- GenAI HAS a Retrievals span type
        # Always emit a Retrievals span (like a RAG retrieval step).
        # When stale_retrieval fault is active, we still can't detect it
        # because GenAI Retrievals has no staleness attribute.
        with tracer.start_as_current_span(
            "retrieve-context",
            kind=SpanKind.CLIENT,
            attributes={
                GENAI_OPERATION_NAME: "retrieve",
                GENAI_SYSTEM: "custom_rag",
                GENAI_DATA_SOURCE_ID: "knowledge_base_v1",
            },
        ):
            results["steps"].append({"type": "retrieval", "source": "knowledge_base_v1"})

        # 3. Agent loop: LLM call -> maybe tool -> repeat
        messages: List[Dict[str, Any]] = [{"role": "user", "content": task}]
        iteration = 0
        current_agent = "researcher"

        while iteration < max_iterations:
            iteration += 1

            # Reasoning step -- GenAI has no reasoning span type.
            with tracer.start_as_current_span(f"reason-{iteration}"):
                results["steps"].append({"type": "reasoning", "iteration": iteration})

            # LLM call -- GenAI Inference span (CLIENT kind)
            with tracer.start_as_current_span(
                f"chat {model}",
                kind=SpanKind.CLIENT,
                attributes={
                    GENAI_OPERATION_NAME: "chat",
                    GENAI_REQUEST_MODEL: model,
                    GENAI_SYSTEM: "anthropic" if "claude" in model else "openai",
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
                        llm_span.set_attribute(GENAI_USAGE_INPUT_TOKENS, 0)
                        llm_span.set_attribute(GENAI_USAGE_OUTPUT_TOKENS, 0)
                        results["steps"].append({"type": "llm_timeout", "error": str(e)})
                        break

                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    llm_span.set_attribute(GENAI_USAGE_INPUT_TOKENS, input_tokens)
                    llm_span.set_attribute(GENAI_USAGE_OUTPUT_TOKENS, output_tokens)
                    llm_span.set_attribute(GENAI_RESPONSE_MODEL, model)

                    # Process response
                    has_tool_use = False
                    for block in response.content:
                        if block.type == "tool_use":
                            has_tool_use = True

                            if block.name == "delegate_task":
                                # GenAI has NO delegation span type.
                                # We can only use a generic span.
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

                            # Execute Tool -- GenAI Execute Tool span (INTERNAL kind)
                            tool_start = time.time()
                            with tracer.start_as_current_span(
                                f"execute_tool",
                                kind=SpanKind.INTERNAL,
                                attributes={
                                    GENAI_TOOL_NAME: block.name,
                                    GENAI_TOOL_CALL_ID: block.id,
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
                    llm_span.set_attribute(GENAI_USAGE_INPUT_TOKENS, 500)
                    llm_span.set_attribute(GENAI_USAGE_OUTPUT_TOKENS, 200)
                    results["final_answer"] = "Demo response without mock client."
                    break

        results["iterations"] = iteration

        # 4. Guard rail check -- GenAI has no guardrail span type.
        with tracer.start_as_current_span("content-safety"):
            results["steps"].append({"type": "guardrail", "result": "pass"})

        # 5. Store to memory -- GenAI has no memory span type.
        with tracer.start_as_current_span("store-memory"):
            results["steps"].append({"type": "memory_write"})

    return results
