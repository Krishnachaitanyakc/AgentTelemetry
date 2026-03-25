"""CrewAI instrumentation adapter.

Uses CrewAI's hook system (no monkey-patching) to capture LLM_CALL and
TOOL_CALL spans.
"""

from __future__ import annotations

import time
from typing import Any, Collection, Dict, Optional

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import StatusCode

from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    AGENT_FRAMEWORK,
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_TASK,
    AgentSpanKind,
    LLM_COMPLETION,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_LATENCY_MS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    LLM_PROMPT,
    LLM_PROVIDER,
    LLM_TOTAL_TOKENS,
    TOOL_INPUT,
    TOOL_LATENCY_MS,
    TOOL_NAME,
    TOOL_OUTPUT,
    TOOL_STATUS,
    estimate_cost,
)
from agenttelemetry.core.privacy import PrivacyLevel, filter_attributes, should_capture_content


class CrewAIInstrumentor(BaseInstrumentor):
    """Instruments CrewAI via its global hook system."""

    _tracer: Optional[trace.Tracer] = None
    _privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY
    _llm_start_times: Dict[str, float] = {}
    _tool_start_times: Dict[str, float] = {}
    _active_llm_spans: Dict[str, trace.Span] = {}
    _active_tool_spans: Dict[str, trace.Span] = {}

    def instrumentation_dependencies(self) -> Collection[str]:
        return ("crewai >= 0.28.0",)

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider")
        self._privacy_level = kwargs.get("privacy_level", PrivacyLevel.METADATA_ONLY)
        self._tracer = trace.get_tracer(
            "agenttelemetry.crewai", "0.1.0", tracer_provider=tracer_provider
        )
        self._llm_start_times = {}
        self._tool_start_times = {}
        self._active_llm_spans = {}
        self._active_tool_spans = {}

        try:
            from crewai.utilities.hooks import (
                register_before_llm_call_hook,
                register_after_llm_call_hook,
                register_before_tool_call_hook,
                register_after_tool_call_hook,
            )
        except ImportError as exc:
            raise ImportError(
                "crewai is required for CrewAIInstrumentor. "
                "Install it with: pip install crewai"
            ) from exc

        instrumentor = self

        def before_llm(context: Any) -> None:
            instrumentor._on_before_llm(context)

        def after_llm(context: Any) -> None:
            instrumentor._on_after_llm(context)

        def before_tool(context: Any) -> None:
            instrumentor._on_before_tool(context)

        def after_tool(context: Any) -> None:
            instrumentor._on_after_tool(context)

        register_before_llm_call_hook(before_llm)
        register_after_llm_call_hook(after_llm)
        register_before_tool_call_hook(before_tool)
        register_after_tool_call_hook(after_tool)

    def _uninstrument(self, **kwargs: Any) -> None:
        try:
            from crewai.utilities.hooks import clear_all_global_hooks
            clear_all_global_hooks()
        except ImportError:
            pass

        # End any active spans
        for span in self._active_llm_spans.values():
            span.end()
        for span in self._active_tool_spans.values():
            span.end()
        self._active_llm_spans.clear()
        self._active_tool_spans.clear()
        self._llm_start_times.clear()
        self._tool_start_times.clear()

    def _get_context_id(self, context: Any) -> str:
        """Extract a unique ID from a CrewAI hook context object."""
        # CrewAI hook contexts typically have an id or can be hashed
        ctx_id = getattr(context, "id", None)
        if ctx_id:
            return str(ctx_id)
        return str(id(context))

    def _get_agent_info(self, context: Any) -> Dict[str, Any]:
        """Extract agent metadata from context."""
        attrs: Dict[str, Any] = {AGENT_FRAMEWORK: "crewai"}
        agent = getattr(context, "agent", None)
        if agent:
            attrs[AGENT_NAME] = getattr(agent, "role", "unknown")
            role = getattr(agent, "role", None)
            if role:
                attrs[AGENT_ROLE] = role
        task = getattr(context, "task", None)
        if task:
            desc = getattr(task, "description", None)
            if desc:
                attrs[AGENT_TASK] = str(desc)[:200]
        return attrs

    def _on_before_llm(self, context: Any) -> None:
        ctx_id = self._get_context_id(context)
        self._llm_start_times[ctx_id] = time.perf_counter()

        model = getattr(context, "model", "") or ""
        attrs: Dict[str, Any] = {
            AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
            LLM_PROVIDER: "crewai",
            LLM_MODEL: model,
        }
        attrs.update(self._get_agent_info(context))

        if should_capture_content(self._privacy_level):
            prompt = getattr(context, "prompt", None) or getattr(context, "messages", None)
            if prompt:
                attrs[LLM_PROMPT] = str(prompt)

        filtered = filter_attributes(attrs, self._privacy_level)
        span = self._tracer.start_span(
            "crewai.llm_call",
            kind=trace.SpanKind.INTERNAL,
            attributes=filtered,
        )
        self._active_llm_spans[ctx_id] = span

    def _on_after_llm(self, context: Any) -> None:
        ctx_id = self._get_context_id(context)
        span = self._active_llm_spans.pop(ctx_id, None)
        start_time = self._llm_start_times.pop(ctx_id, None)

        if span is None:
            return

        if start_time is not None:
            latency_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute(LLM_LATENCY_MS, latency_ms)

        # Extract token usage from response
        response = getattr(context, "response", None) or getattr(context, "result", None)
        if response:
            usage = getattr(response, "usage", None)
            if usage:
                input_tokens = getattr(usage, "input_tokens", 0) or getattr(
                    usage, "prompt_tokens", 0
                ) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or getattr(
                    usage, "completion_tokens", 0
                ) or 0
                span.set_attribute(LLM_INPUT_TOKENS, input_tokens)
                span.set_attribute(LLM_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(LLM_TOTAL_TOKENS, input_tokens + output_tokens)
                model = getattr(context, "model", "")
                span.set_attribute(
                    LLM_COST, estimate_cost(model or "", input_tokens, output_tokens)
                )

            if should_capture_content(self._privacy_level):
                text = getattr(response, "text", None) or getattr(response, "content", None)
                if text:
                    span.set_attribute(LLM_COMPLETION, str(text))

        error = getattr(context, "error", None)
        if error:
            span.set_status(StatusCode.ERROR, str(error))
            if isinstance(error, BaseException):
                span.record_exception(error)

        span.end()

    def _on_before_tool(self, context: Any) -> None:
        ctx_id = self._get_context_id(context)
        self._tool_start_times[ctx_id] = time.perf_counter()

        tool_name = getattr(context, "tool_name", "unknown") or getattr(
            context, "name", "unknown"
        )
        attrs: Dict[str, Any] = {
            AGENT_SPAN_KIND: AgentSpanKind.TOOL_CALL,
            TOOL_NAME: str(tool_name),
        }
        attrs.update(self._get_agent_info(context))

        if should_capture_content(self._privacy_level):
            tool_input = getattr(context, "input", None) or getattr(
                context, "tool_input", None
            )
            if tool_input:
                attrs[TOOL_INPUT] = str(tool_input)

        filtered = filter_attributes(attrs, self._privacy_level)
        span = self._tracer.start_span(
            f"crewai.tool.{tool_name}",
            kind=trace.SpanKind.INTERNAL,
            attributes=filtered,
        )
        self._active_tool_spans[ctx_id] = span

    def _on_after_tool(self, context: Any) -> None:
        ctx_id = self._get_context_id(context)
        span = self._active_tool_spans.pop(ctx_id, None)
        start_time = self._tool_start_times.pop(ctx_id, None)

        if span is None:
            return

        if start_time is not None:
            latency_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute(TOOL_LATENCY_MS, latency_ms)

        error = getattr(context, "error", None)
        if error:
            span.set_attribute(TOOL_STATUS, "error")
            span.set_status(StatusCode.ERROR, str(error))
            if isinstance(error, BaseException):
                span.record_exception(error)
        else:
            span.set_attribute(TOOL_STATUS, "success")

        if should_capture_content(self._privacy_level):
            output = getattr(context, "output", None) or getattr(
                context, "result", None
            )
            if output:
                span.set_attribute(TOOL_OUTPUT, str(output))

        span.end()
