"""LangChain instrumentation adapter.

Uses LangChain's callback handler pattern (no monkey-patching).
Creates a dynamic BaseCallbackHandler subclass at instrument time to avoid
import-time dependency on langchain.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Collection, Dict, List, Optional, Sequence

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
    TOOL_LATENCY_MS,
    TOOL_NAME,
    TOOL_OUTPUT,
    TOOL_STATUS,
    estimate_cost,
)
from agenttelemetry.core.privacy import PrivacyLevel, filter_attributes, should_capture_content


class LangChainInstrumentor(BaseInstrumentor):
    """Instruments LangChain via callback handlers."""

    _tracer: Optional[trace.Tracer] = None
    _privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY
    _handler_class: Any = None
    _handler_instance: Any = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return ("langchain-core >= 0.1.0",)

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider")
        self._privacy_level = kwargs.get("privacy_level", PrivacyLevel.METADATA_ONLY)
        self._tracer = trace.get_tracer(
            "agenttelemetry.langchain", "0.1.0", tracer_provider=tracer_provider
        )

        try:
            from langchain_core.callbacks.base import BaseCallbackHandler
        except ImportError as exc:
            raise ImportError(
                "langchain-core is required for LangChainInstrumentor. "
                "Install it with: pip install langchain-core"
            ) from exc

        tracer = self._tracer
        privacy_level = self._privacy_level

        class AgentTelemetryCallbackHandler(BaseCallbackHandler):
            """LangChain callback handler that emits OTel spans."""

            def __init__(self) -> None:
                super().__init__()
                self._run_spans: Dict[str, trace.Span] = {}
                self._run_start_times: Dict[str, float] = {}

            def _start_span(
                self, run_id: uuid.UUID, name: str, attrs: Dict[str, Any]
            ) -> trace.Span:
                filtered = filter_attributes(attrs, privacy_level)
                span = tracer.start_span(
                    name, kind=trace.SpanKind.INTERNAL, attributes=filtered
                )
                key = str(run_id)
                self._run_spans[key] = span
                self._run_start_times[key] = time.perf_counter()
                return span

            def _end_span(
                self,
                run_id: uuid.UUID,
                extra_attrs: Optional[Dict[str, Any]] = None,
                error: Optional[BaseException] = None,
            ) -> None:
                key = str(run_id)
                span = self._run_spans.pop(key, None)
                start_time = self._run_start_times.pop(key, None)
                if span is None:
                    return
                if extra_attrs:
                    filtered = filter_attributes(extra_attrs, privacy_level)
                    for k, v in filtered.items():
                        span.set_attribute(k, v)
                if start_time is not None:
                    latency = (time.perf_counter() - start_time) * 1000
                    span.set_attribute(LLM_LATENCY_MS, latency)
                if error:
                    span.set_status(StatusCode.ERROR, str(error))
                    span.record_exception(error)
                span.end()

            # -- Chain callbacks --

            def on_chain_start(
                self,
                serialized: Dict[str, Any],
                inputs: Dict[str, Any],
                *,
                run_id: uuid.UUID,
                parent_run_id: Optional[uuid.UUID] = None,
                **kw: Any,
            ) -> None:
                serialized = serialized or {}
                name_parts = serialized.get("id") or ["", "", "", "unknown"]
                class_name = name_parts[-1] if name_parts else "chain"
                # Also check metadata/tags for agent hints
                tags = kw.get("tags") or []
                metadata = kw.get("metadata") or {}
                is_agent = (
                    "agent" in class_name.lower()
                    or "executor" in class_name.lower()
                    or any("agent" in str(t).lower() for t in tags)
                    or "agent" in str(metadata.get("langgraph_node", "")).lower()
                )
                kind = AgentSpanKind.AGENT if is_agent else AgentSpanKind.REASONING
                attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: kind,
                    AGENT_FRAMEWORK: "langchain",
                    AGENT_NAME: class_name,
                }
                self._start_span(run_id, f"langchain.{class_name}", attrs)

            def on_chain_end(
                self,
                outputs: Dict[str, Any],
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                self._end_span(run_id)

            def on_chain_error(
                self,
                error: BaseException,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                self._end_span(run_id, error=error)

            # -- LLM callbacks --

            def on_llm_start(
                self,
                serialized: Dict[str, Any],
                prompts: List[str],
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                serialized = serialized or {}
                model_name = serialized.get("kwargs", {}).get("model_name", "")
                if not model_name:
                    model_name = serialized.get("kwargs", {}).get("model", "")
                # Try invocation_params for newer LangChain
                inv_params = kw.get("invocation_params") or {}
                if not model_name:
                    model_name = inv_params.get("model_name", inv_params.get("model", ""))
                attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
                    LLM_PROVIDER: "langchain",
                    LLM_MODEL: model_name,
                }
                if should_capture_content(privacy_level):
                    attrs[LLM_PROMPT] = str(prompts)
                self._start_span(run_id, "langchain.llm", attrs)

            def on_chat_model_start(
                self,
                serialized: Dict[str, Any],
                messages: List[Any],
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                serialized = serialized or {}
                model_name = serialized.get("kwargs", {}).get("model_name", "")
                if not model_name:
                    model_name = serialized.get("kwargs", {}).get("model", "")
                inv_params = kw.get("invocation_params") or {}
                if not model_name:
                    model_name = inv_params.get("model_name", inv_params.get("model", ""))
                attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
                    LLM_PROVIDER: "langchain",
                    LLM_MODEL: model_name,
                }
                if should_capture_content(privacy_level):
                    attrs[LLM_PROMPT] = str(messages)
                self._start_span(run_id, "langchain.chat_model", attrs)

            def on_llm_end(
                self,
                response: Any,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                extra: Dict[str, Any] = {}
                # Try multiple paths for token usage (LangChain API evolved)
                llm_output = getattr(response, "llm_output", None) or {}
                token_usage = llm_output.get("token_usage", {})
                model = llm_output.get("model_name", "")

                # Newer LangChain: usage metadata on generation objects
                if not token_usage:
                    generations = getattr(response, "generations", [])
                    for gen_list in generations:
                        for gen in gen_list:
                            usage_meta = getattr(gen, "generation_info", {}) or {}
                            if not token_usage and usage_meta:
                                token_usage = usage_meta
                            msg = getattr(gen, "message", None)
                            if msg:
                                um = getattr(msg, "usage_metadata", None)
                                if um:
                                    token_usage = {
                                        "prompt_tokens": getattr(um, "input_tokens", 0) or um.get("input_tokens", 0) if isinstance(um, dict) else getattr(um, "input_tokens", 0),
                                        "completion_tokens": getattr(um, "output_tokens", 0) or um.get("output_tokens", 0) if isinstance(um, dict) else getattr(um, "output_tokens", 0),
                                    }
                                rm = getattr(msg, "response_metadata", None) or {}
                                if not model and isinstance(rm, dict):
                                    model = rm.get("model_name", rm.get("model", ""))
                                if not token_usage and isinstance(rm, dict) and "token_usage" in rm:
                                    token_usage = rm["token_usage"]

                if token_usage:
                    input_tokens = token_usage.get("prompt_tokens", 0) or 0
                    output_tokens = token_usage.get("completion_tokens", 0) or 0
                    extra[LLM_INPUT_TOKENS] = input_tokens
                    extra[LLM_OUTPUT_TOKENS] = output_tokens
                    extra[LLM_TOTAL_TOKENS] = input_tokens + output_tokens
                    if model:
                        extra[LLM_COST] = estimate_cost(model, input_tokens, output_tokens)
                    extra[LLM_MODEL] = model

                if should_capture_content(privacy_level):
                    generations = getattr(response, "generations", [])
                    texts = []
                    for gen_list in generations:
                        for gen in gen_list:
                            texts.append(getattr(gen, "text", str(gen)))
                    if texts:
                        extra[LLM_COMPLETION] = "\n".join(texts)
                self._end_span(run_id, extra_attrs=extra)

            def on_llm_error(
                self,
                error: BaseException,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                self._end_span(run_id, error=error)

            # -- Tool callbacks --

            def on_tool_start(
                self,
                serialized: Dict[str, Any],
                input_str: str,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                tool_name = serialized.get("name", "unknown")
                attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: AgentSpanKind.TOOL_CALL,
                    TOOL_NAME: tool_name,
                }
                if should_capture_content(privacy_level):
                    attrs[TOOL_INPUT] = input_str
                self._start_span(run_id, f"langchain.tool.{tool_name}", attrs)

            def on_tool_end(
                self,
                output: Any,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                extra: Dict[str, Any] = {TOOL_STATUS: "success"}
                if should_capture_content(privacy_level):
                    extra[TOOL_OUTPUT] = str(output)
                self._end_span(run_id, extra_attrs=extra)

            def on_tool_error(
                self,
                error: BaseException,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                self._end_span(run_id, extra_attrs={TOOL_STATUS: "error"}, error=error)

            # -- Retriever callbacks --

            def on_retriever_start(
                self,
                serialized: Dict[str, Any],
                query: str,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: AgentSpanKind.RETRIEVAL,
                    RETRIEVAL_SOURCE: serialized.get("name", "retriever"),
                }
                if should_capture_content(privacy_level):
                    attrs[RETRIEVAL_QUERY] = query
                self._start_span(run_id, "langchain.retriever", attrs)

            def on_retriever_end(
                self,
                documents: Sequence[Any],
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                self._end_span(
                    run_id,
                    extra_attrs={RETRIEVAL_DOC_COUNT: len(documents)},
                )

            # -- Agent action callback --

            def on_agent_action(
                self,
                action: Any,
                *,
                run_id: uuid.UUID,
                **kw: Any,
            ) -> None:
                attrs: Dict[str, Any] = {
                    AGENT_SPAN_KIND: AgentSpanKind.PLANNING,
                    PLANNING_STRATEGY: "agent_action",
                }
                if should_capture_content(privacy_level):
                    attrs[TOOL_NAME] = getattr(action, "tool", "unknown")
                    attrs[TOOL_INPUT] = str(getattr(action, "tool_input", ""))
                # Planning span is instantaneous — create and end immediately
                span = tracer.start_span(
                    "langchain.agent_action",
                    kind=trace.SpanKind.INTERNAL,
                    attributes=filter_attributes(attrs, privacy_level),
                )
                span.end()

        self._handler_class = AgentTelemetryCallbackHandler
        self._handler_instance = AgentTelemetryCallbackHandler()

    def _uninstrument(self, **kwargs: Any) -> None:
        # Clean up span references
        if self._handler_instance is not None:
            for span in self._handler_instance._run_spans.values():
                span.end()
            self._handler_instance._run_spans.clear()
        self._handler_class = None
        self._handler_instance = None

    def get_callback_handler(self) -> Any:
        """Return a new callback handler instance.

        Use this to add to your LangChain chain's callbacks::

            from agenttelemetry.adapters.langchain import LangChainInstrumentor

            instrumentor = LangChainInstrumentor()
            instrumentor.instrument(tracer_provider=provider, privacy_level=level)
            handler = instrumentor.get_callback_handler()

            chain.invoke(input, config={"callbacks": [handler]})
        """
        if self._handler_class is None:
            raise RuntimeError(
                "LangChainInstrumentor must be instrumented before getting a callback handler. "
                "Call instrument() first."
            )
        return self._handler_class()
