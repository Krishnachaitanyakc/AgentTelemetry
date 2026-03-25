"""Framework adapters for AgentTelemetry.

Each adapter instruments a specific AI agent framework to emit
OpenTelemetry spans with AgentTelemetry semantic attributes.

Adapters with external framework dependencies use lazy imports — the
framework package is only required at ``instrument()`` time, not at
import time.
"""

from agenttelemetry.adapters.anthropic_sdk import AnthropicInstrumentor
from agenttelemetry.adapters.openai_sdk import OpenAIInstrumentor
from agenttelemetry.adapters.langchain import LangChainInstrumentor
from agenttelemetry.adapters.crewai import CrewAIInstrumentor
from agenttelemetry.adapters.llamaindex import LlamaIndexInstrumentor
from agenttelemetry.adapters.autogen import AutoGenInstrumentor
from agenttelemetry.adapters.custom import (
    start_agent_span,
    start_llm_span,
    start_tool_span,
    start_retrieval_span,
    start_agent_span_ctx,
    start_planning_span,
    start_reasoning_span,
    start_guardrail_span,
    start_delegation_span,
    start_memory_span,
)

__all__ = [
    # BaseInstrumentor adapters
    "AnthropicInstrumentor",
    "OpenAIInstrumentor",
    "LangChainInstrumentor",
    "CrewAIInstrumentor",
    "LlamaIndexInstrumentor",
    "AutoGenInstrumentor",
    # Manual instrumentation helpers
    "start_agent_span",
    "start_llm_span",
    "start_tool_span",
    "start_retrieval_span",
    "start_agent_span_ctx",
    "start_planning_span",
    "start_reasoning_span",
    "start_guardrail_span",
    "start_delegation_span",
    "start_memory_span",
]
