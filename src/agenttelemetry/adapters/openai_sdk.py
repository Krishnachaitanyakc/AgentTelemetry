"""OpenAI SDK instrumentation adapter.

Monkey-patches openai.resources.chat.completions to capture LLM_CALL and
TOOL_CALL spans for every Completions.create() call.
"""

from __future__ import annotations

import time
from typing import Any, Collection, Dict, Optional

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import StatusCode

from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    AgentSpanKind,
    LLM_COMPLETION,
    LLM_COST,
    LLM_INPUT_TOKENS,
    LLM_LATENCY_MS,
    LLM_MODEL,
    LLM_OUTPUT_TOKENS,
    LLM_PROMPT,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LLM_TOTAL_TOKENS,
    TOOL_INPUT,
    TOOL_NAME,
    TOOL_STATUS,
    estimate_cost,
)
from agenttelemetry.core.privacy import PrivacyLevel, filter_attributes, should_capture_content


class OpenAIInstrumentor(BaseInstrumentor):
    """Instruments the OpenAI Python SDK."""

    _tracer: Optional[trace.Tracer] = None
    _privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY
    _original_create: Any = None
    _original_async_create: Any = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return ("openai >= 1.0.0",)

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider")
        self._privacy_level = kwargs.get("privacy_level", PrivacyLevel.METADATA_ONLY)
        self._tracer = trace.get_tracer(
            "agenttelemetry.openai", "0.1.0", tracer_provider=tracer_provider
        )

        try:
            import openai.resources.chat.completions as completions_mod
        except ImportError as exc:
            raise ImportError(
                "openai package is required for OpenAIInstrumentor. "
                "Install it with: pip install openai"
            ) from exc

        # Patch sync create
        self._original_create = completions_mod.Completions.create
        instrumentor = self

        def patched_create(self_comp: Any, *args: Any, **kw: Any) -> Any:
            return instrumentor._traced_create(
                self_comp, instrumentor._original_create, *args, **kw
            )

        patched_create.__wrapped__ = self._original_create
        completions_mod.Completions.create = patched_create

        # Patch async create
        self._original_async_create = completions_mod.AsyncCompletions.create
        async_instrumentor = self

        async def patched_async_create(self_comp: Any, *args: Any, **kw: Any) -> Any:
            return await async_instrumentor._traced_async_create(
                self_comp, async_instrumentor._original_async_create, *args, **kw
            )

        patched_async_create.__wrapped__ = self._original_async_create
        completions_mod.AsyncCompletions.create = patched_async_create

    def _uninstrument(self, **kwargs: Any) -> None:
        try:
            import openai.resources.chat.completions as completions_mod
        except ImportError:
            return

        if self._original_create is not None:
            completions_mod.Completions.create = self._original_create
            self._original_create = None

        if self._original_async_create is not None:
            completions_mod.AsyncCompletions.create = self._original_async_create
            self._original_async_create = None

    def _build_llm_attributes(
        self, kwargs: Dict[str, Any], response: Any, latency_ms: float
    ) -> Dict[str, Any]:
        """Build span attributes from request kwargs and response."""
        attrs: Dict[str, Any] = {
            AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
            LLM_PROVIDER: "openai",
            LLM_LATENCY_MS: latency_ms,
        }

        model = kwargs.get("model", "")
        attrs[LLM_MODEL] = model

        if "temperature" in kwargs:
            attrs[LLM_TEMPERATURE] = kwargs["temperature"]

        if should_capture_content(self._privacy_level):
            messages = kwargs.get("messages", [])
            attrs[LLM_PROMPT] = str(messages)

        if response is not None:
            usage = getattr(response, "usage", None)
            if usage:
                input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(usage, "completion_tokens", 0) or 0
                attrs[LLM_INPUT_TOKENS] = input_tokens
                attrs[LLM_OUTPUT_TOKENS] = output_tokens
                attrs[LLM_TOTAL_TOKENS] = input_tokens + output_tokens
                # Use response model if available (may differ from request)
                resp_model = getattr(response, "model", model) or model
                attrs[LLM_COST] = estimate_cost(resp_model, input_tokens, output_tokens)

            if should_capture_content(self._privacy_level):
                choices = getattr(response, "choices", []) or []
                text_parts = []
                for choice in choices:
                    msg = getattr(choice, "message", None)
                    if msg and getattr(msg, "content", None):
                        text_parts.append(msg.content)
                if text_parts:
                    attrs[LLM_COMPLETION] = "\n".join(text_parts)

        return filter_attributes(attrs, self._privacy_level)

    def _create_tool_spans(self, response: Any) -> None:
        """Create TOOL_CALL child spans for function/tool calls in the response."""
        choices = getattr(response, "choices", []) or []
        for choice in choices:
            msg = getattr(choice, "message", None)
            if msg is None:
                continue
            tool_calls = getattr(msg, "tool_calls", None) or []
            for tc in tool_calls:
                func = getattr(tc, "function", None)
                if func is None:
                    continue
                tool_name = getattr(func, "name", "unknown")
                tool_attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: AgentSpanKind.TOOL_CALL,
                    TOOL_NAME: tool_name,
                    TOOL_STATUS: "requested",
                }
                if should_capture_content(self._privacy_level):
                    tool_attrs[TOOL_INPUT] = getattr(func, "arguments", "")
                filtered = filter_attributes(tool_attrs, self._privacy_level)
                with self._tracer.start_as_current_span(
                    f"tool.{tool_name}",
                    kind=trace.SpanKind.INTERNAL,
                    attributes=filtered,
                ):
                    pass  # Span records the tool request

    def _traced_create(
        self, self_comp: Any, original: Any, *args: Any, **kwargs: Any
    ) -> Any:
        start = time.perf_counter()
        try:
            response = original(self_comp, *args, **kwargs)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            attrs = filter_attributes(
                {
                    AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
                    LLM_PROVIDER: "openai",
                    LLM_MODEL: kwargs.get("model", ""),
                    LLM_LATENCY_MS: latency_ms,
                },
                self._privacy_level,
            )
            with self._tracer.start_as_current_span(
                "openai.chat.completions.create",
                kind=trace.SpanKind.INTERNAL,
                attributes=attrs,
            ) as span:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        attrs = self._build_llm_attributes(kwargs, response, latency_ms)
        with self._tracer.start_as_current_span(
            "openai.chat.completions.create",
            kind=trace.SpanKind.INTERNAL,
            attributes=attrs,
        ):
            self._create_tool_spans(response)

        return response

    async def _traced_async_create(
        self, self_comp: Any, original: Any, *args: Any, **kwargs: Any
    ) -> Any:
        start = time.perf_counter()
        try:
            response = await original(self_comp, *args, **kwargs)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            attrs = filter_attributes(
                {
                    AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
                    LLM_PROVIDER: "openai",
                    LLM_MODEL: kwargs.get("model", ""),
                    LLM_LATENCY_MS: latency_ms,
                },
                self._privacy_level,
            )
            with self._tracer.start_as_current_span(
                "openai.chat.completions.create",
                kind=trace.SpanKind.INTERNAL,
                attributes=attrs,
            ) as span:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        attrs = self._build_llm_attributes(kwargs, response, latency_ms)
        with self._tracer.start_as_current_span(
            "openai.chat.completions.create",
            kind=trace.SpanKind.INTERNAL,
            attributes=attrs,
        ):
            self._create_tool_spans(response)

        return response
