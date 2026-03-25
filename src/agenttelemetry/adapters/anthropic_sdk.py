"""Anthropic SDK instrumentation adapter.

Monkey-patches anthropic.resources.messages to capture LLM_CALL and
TOOL_CALL spans for every Messages.create() and AsyncMessages.create() call.
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


class AnthropicInstrumentor(BaseInstrumentor):
    """Instruments the Anthropic Python SDK."""

    _tracer: Optional[trace.Tracer] = None
    _privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY
    _original_create: Any = None
    _original_async_create: Any = None
    _original_stream: Any = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return ("anthropic >= 0.18.0",)

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider")
        self._privacy_level = kwargs.get("privacy_level", PrivacyLevel.METADATA_ONLY)
        self._tracer = trace.get_tracer(
            "agenttelemetry.anthropic", "0.1.0", tracer_provider=tracer_provider
        )

        try:
            import anthropic.resources.messages as messages_mod
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required for AnthropicInstrumentor. "
                "Install it with: pip install anthropic"
            ) from exc

        # Patch sync create
        self._original_create = messages_mod.Messages.create
        instrumentor = self

        def patched_create(self_msg: Any, *args: Any, **kw: Any) -> Any:
            return instrumentor._traced_create(
                self_msg, instrumentor._original_create, *args, **kw
            )

        patched_create.__wrapped__ = self._original_create
        messages_mod.Messages.create = patched_create

        # Patch async create
        self._original_async_create = messages_mod.AsyncMessages.create
        async_instrumentor = self

        async def patched_async_create(self_msg: Any, *args: Any, **kw: Any) -> Any:
            return await async_instrumentor._traced_async_create(
                self_msg, async_instrumentor._original_async_create, *args, **kw
            )

        patched_async_create.__wrapped__ = self._original_async_create
        messages_mod.AsyncMessages.create = patched_async_create

        # Patch stream
        if hasattr(messages_mod.Messages, "stream"):
            self._original_stream = messages_mod.Messages.stream
            stream_instrumentor = self

            def patched_stream(self_msg: Any, *args: Any, **kw: Any) -> Any:
                return stream_instrumentor._traced_stream(
                    self_msg, stream_instrumentor._original_stream, *args, **kw
                )

            patched_stream.__wrapped__ = self._original_stream
            messages_mod.Messages.stream = patched_stream

    def _uninstrument(self, **kwargs: Any) -> None:
        try:
            import anthropic.resources.messages as messages_mod
        except ImportError:
            return

        if self._original_create is not None:
            messages_mod.Messages.create = self._original_create
            self._original_create = None

        if self._original_async_create is not None:
            messages_mod.AsyncMessages.create = self._original_async_create
            self._original_async_create = None

        if self._original_stream is not None:
            messages_mod.Messages.stream = self._original_stream
            self._original_stream = None

    def _build_llm_attributes(
        self, kwargs: Dict[str, Any], response: Any, latency_ms: float
    ) -> Dict[str, Any]:
        """Build span attributes from request kwargs and response."""
        attrs: Dict[str, Any] = {
            AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
            LLM_PROVIDER: "anthropic",
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
                input_tokens = getattr(usage, "input_tokens", 0)
                output_tokens = getattr(usage, "output_tokens", 0)
                attrs[LLM_INPUT_TOKENS] = input_tokens
                attrs[LLM_OUTPUT_TOKENS] = output_tokens
                attrs[LLM_TOTAL_TOKENS] = input_tokens + output_tokens
                attrs[LLM_COST] = estimate_cost(model, input_tokens, output_tokens)

            if should_capture_content(self._privacy_level):
                content = getattr(response, "content", [])
                text_parts = []
                for block in content:
                    if getattr(block, "type", None) == "text":
                        text_parts.append(getattr(block, "text", ""))
                attrs[LLM_COMPLETION] = "\n".join(text_parts)

        return filter_attributes(attrs, self._privacy_level)

    def _create_tool_spans(self, response: Any) -> None:
        """Create TOOL_CALL child spans for any tool_use blocks in the response."""
        content = getattr(response, "content", [])
        for block in content:
            if getattr(block, "type", None) == "tool_use":
                tool_attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: AgentSpanKind.TOOL_CALL,
                    TOOL_NAME: getattr(block, "name", "unknown"),
                    TOOL_STATUS: "requested",
                }
                if should_capture_content(self._privacy_level):
                    tool_attrs[TOOL_INPUT] = str(getattr(block, "input", {}))
                filtered = filter_attributes(tool_attrs, self._privacy_level)
                with self._tracer.start_as_current_span(
                    f"tool.{getattr(block, 'name', 'unknown')}",
                    kind=trace.SpanKind.INTERNAL,
                    attributes=filtered,
                ):
                    pass  # Span just records the tool request

    def _traced_create(
        self, self_msg: Any, original: Any, *args: Any, **kwargs: Any
    ) -> Any:
        start = time.perf_counter()
        try:
            response = original(self_msg, *args, **kwargs)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            attrs = filter_attributes(
                {
                    AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
                    LLM_PROVIDER: "anthropic",
                    LLM_MODEL: kwargs.get("model", ""),
                    LLM_LATENCY_MS: latency_ms,
                },
                self._privacy_level,
            )
            with self._tracer.start_as_current_span(
                "anthropic.messages.create",
                kind=trace.SpanKind.INTERNAL,
                attributes=attrs,
            ) as span:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        attrs = self._build_llm_attributes(kwargs, response, latency_ms)
        with self._tracer.start_as_current_span(
            "anthropic.messages.create",
            kind=trace.SpanKind.INTERNAL,
            attributes=attrs,
        ):
            self._create_tool_spans(response)

        return response

    async def _traced_async_create(
        self, self_msg: Any, original: Any, *args: Any, **kwargs: Any
    ) -> Any:
        start = time.perf_counter()
        try:
            response = await original(self_msg, *args, **kwargs)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            attrs = filter_attributes(
                {
                    AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
                    LLM_PROVIDER: "anthropic",
                    LLM_MODEL: kwargs.get("model", ""),
                    LLM_LATENCY_MS: latency_ms,
                },
                self._privacy_level,
            )
            with self._tracer.start_as_current_span(
                "anthropic.messages.create",
                kind=trace.SpanKind.INTERNAL,
                attributes=attrs,
            ) as span:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        attrs = self._build_llm_attributes(kwargs, response, latency_ms)
        with self._tracer.start_as_current_span(
            "anthropic.messages.create",
            kind=trace.SpanKind.INTERNAL,
            attributes=attrs,
        ):
            self._create_tool_spans(response)

        return response

    def _traced_stream(
        self, self_msg: Any, original: Any, *args: Any, **kwargs: Any
    ) -> Any:
        """Wrap the stream context manager to capture a span on exit."""
        stream_ctx = original(self_msg, *args, **kwargs)
        instrumentor = self
        start = time.perf_counter()

        class _InstrumentedStream:
            """Wraps the Anthropic MessageStream to emit a span when complete."""

            def __init__(self, ctx: Any) -> None:
                self._ctx = ctx
                self._stream = None

            def __enter__(self) -> Any:
                self._stream = self._ctx.__enter__()
                return self._stream

            def __exit__(self, *exc_info: Any) -> Any:
                result = self._ctx.__exit__(*exc_info)
                latency_ms = (time.perf_counter() - start) * 1000
                # After stream completes, get_final_message() has the full response
                response = None
                if self._stream is not None:
                    try:
                        response = self._stream.get_final_message()
                    except Exception:
                        pass
                attrs = instrumentor._build_llm_attributes(
                    kwargs, response, latency_ms
                )
                with instrumentor._tracer.start_as_current_span(
                    "anthropic.messages.stream",
                    kind=trace.SpanKind.INTERNAL,
                    attributes=attrs,
                ):
                    if response is not None:
                        instrumentor._create_tool_spans(response)
                return result

        return _InstrumentedStream(stream_ctx)
