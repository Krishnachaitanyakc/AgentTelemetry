"""LlamaIndex instrumentation adapter.

Uses LlamaIndex's instrumentation module (no monkey-patching) with a custom
BaseSpanHandler subclass to map LlamaIndex operations to AgentTelemetry spans.
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
    PLANNING_STRATEGY,
    RETRIEVAL_DOC_COUNT,
    RETRIEVAL_QUERY,
    RETRIEVAL_SOURCE,
    TOOL_INPUT,
    TOOL_NAME,
    TOOL_OUTPUT,
    TOOL_STATUS,
    estimate_cost,
)
from agenttelemetry.core.privacy import PrivacyLevel, filter_attributes, should_capture_content


# Operation type patterns for classifying LlamaIndex spans
_QUERY_PATTERNS = {"query", "queryengine", "query_engine"}
_RETRIEVER_PATTERNS = {"retrieve", "retriever", "retrieval"}
_LLM_PATTERNS = {"llm", "predict", "completion", "chat"}
_SUB_QUESTION_PATTERNS = {"sub_question", "subquestion", "decompose"}


def _classify_span(span_id: str) -> str:
    """Classify a LlamaIndex span type string into an AgentSpanKind."""
    lower = span_id.lower()
    for pattern in _LLM_PATTERNS:
        if pattern in lower:
            return AgentSpanKind.LLM_CALL
    for pattern in _RETRIEVER_PATTERNS:
        if pattern in lower:
            return AgentSpanKind.RETRIEVAL
    for pattern in _SUB_QUESTION_PATTERNS:
        if pattern in lower:
            return AgentSpanKind.PLANNING
    for pattern in _QUERY_PATTERNS:
        if pattern in lower:
            return AgentSpanKind.AGENT
    return AgentSpanKind.REASONING


class LlamaIndexInstrumentor(BaseInstrumentor):
    """Instruments LlamaIndex via its instrumentation module."""

    _tracer: Optional[trace.Tracer] = None
    _privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY
    _span_handler: Any = None
    _dispatcher_handle: Any = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return ("llama-index-core >= 0.10.0",)

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider")
        self._privacy_level = kwargs.get("privacy_level", PrivacyLevel.METADATA_ONLY)
        self._tracer = trace.get_tracer(
            "agenttelemetry.llamaindex", "0.1.0", tracer_provider=tracer_provider
        )

        try:
            from llama_index.core.instrumentation import get_dispatcher
            from llama_index.core.instrumentation.span_handlers import BaseSpanHandler
            from llama_index.core.instrumentation.span import BaseSpan
        except ImportError as exc:
            raise ImportError(
                "llama-index-core is required for LlamaIndexInstrumentor. "
                "Install it with: pip install llama-index-core"
            ) from exc

        otel_tracer = self._tracer
        privacy_level = self._privacy_level

        class AgentTelemetrySpanHandler(BaseSpanHandler[BaseSpan]):
            """LlamaIndex span handler that emits OTel spans."""

            @classmethod
            def class_name(cls) -> str:
                return "AgentTelemetrySpanHandler"

            def __init__(self) -> None:
                super().__init__()
                self._otel_spans: Dict[str, trace.Span] = {}
                self._start_times: Dict[str, float] = {}

            def span_enter(
                self,
                id_: str,
                bound_args: Any,
                instance: Optional[Any] = None,
                parent_id: Optional[str] = None,
                **kwargs: Any,
            ) -> None:
                kind = _classify_span(id_)
                attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: kind,
                    AGENT_FRAMEWORK: "llamaindex",
                }

                # Extract additional attributes based on span kind
                if kind == AgentSpanKind.LLM_CALL:
                    if instance is not None:
                        model = getattr(instance, "model", None) or getattr(
                            instance, "model_name", None
                        )
                        if model:
                            attrs[LLM_MODEL] = str(model)
                    attrs[LLM_PROVIDER] = "llamaindex"
                    if should_capture_content(privacy_level) and bound_args:
                        prompt_arg = (
                            bound_args.arguments.get("prompt", None)
                            or bound_args.arguments.get("messages", None)
                        )
                        if prompt_arg:
                            attrs[LLM_PROMPT] = str(prompt_arg)

                elif kind == AgentSpanKind.RETRIEVAL:
                    if instance is not None:
                        attrs[RETRIEVAL_SOURCE] = type(instance).__name__
                    if should_capture_content(privacy_level) and bound_args:
                        query = bound_args.arguments.get("query_str", None) or bound_args.arguments.get(
                            "query_bundle", None
                        )
                        if query:
                            attrs[RETRIEVAL_QUERY] = str(query)

                elif kind == AgentSpanKind.PLANNING:
                    attrs[PLANNING_STRATEGY] = "sub_question_decomposition"

                elif kind == AgentSpanKind.AGENT:
                    if instance is not None:
                        attrs[AGENT_NAME] = type(instance).__name__

                filtered = filter_attributes(attrs, privacy_level)
                span = otel_tracer.start_span(
                    f"llamaindex.{id_}",
                    kind=trace.SpanKind.INTERNAL,
                    attributes=filtered,
                )
                self._otel_spans[id_] = span
                self._start_times[id_] = time.perf_counter()

            def span_exit(
                self,
                id_: str,
                bound_args: Any,
                instance: Optional[Any] = None,
                result: Optional[Any] = None,
                **kwargs: Any,
            ) -> None:
                span = self._otel_spans.pop(id_, None)
                start_time = self._start_times.pop(id_, None)
                if span is None:
                    return

                if start_time is not None:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    span.set_attribute(LLM_LATENCY_MS, latency_ms)

                kind = _classify_span(id_)

                # Extract result attributes
                if kind == AgentSpanKind.LLM_CALL and result is not None:
                    # LlamaIndex LLM responses have raw dict or response objects
                    raw = getattr(result, "raw", None)
                    if raw:
                        usage = getattr(raw, "usage", None)
                        if usage:
                            input_tokens = getattr(usage, "prompt_tokens", 0) or getattr(
                                usage, "input_tokens", 0
                            ) or 0
                            output_tokens = getattr(usage, "completion_tokens", 0) or getattr(
                                usage, "output_tokens", 0
                            ) or 0
                            span.set_attribute(LLM_INPUT_TOKENS, input_tokens)
                            span.set_attribute(LLM_OUTPUT_TOKENS, output_tokens)
                            span.set_attribute(LLM_TOTAL_TOKENS, input_tokens + output_tokens)
                            model = span.attributes.get(LLM_MODEL, "") if hasattr(span, 'attributes') else ""
                            span.set_attribute(
                                LLM_COST,
                                estimate_cost(model or "", input_tokens, output_tokens),
                            )
                    if should_capture_content(privacy_level):
                        text = getattr(result, "text", None) or str(result)
                        span.set_attribute(LLM_COMPLETION, text)

                elif kind == AgentSpanKind.RETRIEVAL and result is not None:
                    if isinstance(result, (list, tuple)):
                        span.set_attribute(RETRIEVAL_DOC_COUNT, len(result))

                span.end()

            def span_drop(
                self,
                id_: str,
                bound_args: Any,
                instance: Optional[Any] = None,
                err: Optional[BaseException] = None,
                **kwargs: Any,
            ) -> None:
                span = self._otel_spans.pop(id_, None)
                self._start_times.pop(id_, None)
                if span is None:
                    return
                if err:
                    span.set_status(StatusCode.ERROR, str(err))
                    span.record_exception(err)
                span.end()

            def prepare_to_exit_span(
                self,
                id_: str,
                bound_args: Any,
                instance: Optional[Any] = None,
                result: Optional[Any] = None,
                **kwargs: Any,
            ) -> Any:
                return result

            def prepare_to_drop_span(
                self,
                id_: str,
                bound_args: Any,
                instance: Optional[Any] = None,
                err: Optional[BaseException] = None,
                **kwargs: Any,
            ) -> Any:
                return err

        self._span_handler = AgentTelemetrySpanHandler()

        # Register with root dispatcher
        dispatcher = get_dispatcher()
        dispatcher.add_span_handler(self._span_handler)

    def _uninstrument(self, **kwargs: Any) -> None:
        if self._span_handler is None:
            return

        try:
            from llama_index.core.instrumentation import get_dispatcher
            dispatcher = get_dispatcher()
            # Remove our handler from the dispatcher
            handlers = getattr(dispatcher, "span_handlers", [])
            updated = [h for h in handlers if h is not self._span_handler]
            dispatcher.span_handlers = updated
        except (ImportError, AttributeError):
            pass

        # End any active spans
        for span in self._span_handler._otel_spans.values():
            span.end()
        self._span_handler._otel_spans.clear()
        self._span_handler._start_times.clear()
        self._span_handler = None
