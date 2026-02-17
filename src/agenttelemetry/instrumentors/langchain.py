"""LangChain / LangGraph instrumentor for AgentTelemetry.

Automatically captures telemetry from LangChain and LangGraph applications
by injecting a callback handler into LangChain's global callback system.

Supported events:
    - LLM calls (on_llm_start / on_llm_end / on_llm_error)
    - Tool calls (on_tool_start / on_tool_end / on_tool_error)
    - Chain execution (on_chain_start / on_chain_end / on_chain_error)
    - Agent actions (on_agent_action / on_agent_finish)

Each event is mapped to an AgentTelemetry span:
    - LLM calls    -> AgentSpanKind.LLM_CALL
    - Tool calls   -> AgentSpanKind.TOOL_CALL
    - Agent actions -> AgentSpanKind.REASONING
    - Chains       -> AgentSpanKind.TASK

Usage::

    from agenttelemetry.instrumentors.langchain import LangChainInstrumentor

    instrumentor = LangChainInstrumentor(capture_content=True)
    instrumentor.instrument()

    # Use LangChain / LangGraph as normal -- telemetry captured automatically.

    instrumentor.uninstrument()
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Union

from agenttelemetry.core.events import EventType
from agenttelemetry.core.trace import (
    ATTR_LLM_COMPLETION,
    ATTR_LLM_COST_USD,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_LATENCY_MS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_LLM_PROVIDER,
    ATTR_LLM_TEMPERATURE,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_TOOL_ERROR,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_LATENCY_MS,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    AgentSpan,
    AgentSpanKind,
    AgentTracer,
    SpanStatus,
    estimate_cost,
)
from agenttelemetry.instrumentors.base import BaseInstrumentor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_serialize(obj: Any, max_length: int = 4096) -> str:
    """Serialize an object to a JSON string, truncating if necessary.

    Falls back to ``str()`` for objects that are not JSON-serializable.
    """
    try:
        text = json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError, OverflowError):
        text = str(obj)
    if len(text) > max_length:
        return text[:max_length] + "...[truncated]"
    return text


def _extract_model_name(serialized: Dict[str, Any]) -> str:
    """Best-effort extraction of the model name from LangChain serialized kwargs."""
    # ChatOpenAI, ChatAnthropic, etc. put model in invocation_params or kwargs
    kwargs = serialized.get("kwargs", {})
    for key in ("model_name", "model", "model_id"):
        val = kwargs.get(key)
        if val:
            return str(val)
    # Fallback: invocation_params (set by some providers)
    inv = kwargs.get("invocation_params", {})
    for key in ("model_name", "model", "model_id", "engine"):
        val = inv.get(key)
        if val:
            return str(val)
    # Last resort: class name gives a hint
    name_parts: List[str] = serialized.get("id", [])
    if name_parts:
        return name_parts[-1]
    return "unknown"


def _extract_provider(serialized: Dict[str, Any]) -> str:
    """Infer the LLM provider from the serialized representation."""
    name_parts: List[str] = serialized.get("id", [])
    class_name = name_parts[-1].lower() if name_parts else ""
    if "openai" in class_name:
        return "openai"
    if "anthropic" in class_name:
        return "anthropic"
    if "google" in class_name or "gemini" in class_name:
        return "google"
    if "cohere" in class_name:
        return "cohere"
    if "huggingface" in class_name or "hf" in class_name:
        return "huggingface"
    if "bedrock" in class_name:
        return "aws_bedrock"
    if "azure" in class_name:
        return "azure_openai"
    return "unknown"


def _extract_temperature(serialized: Dict[str, Any]) -> Optional[float]:
    """Extract temperature from serialized kwargs if present."""
    kwargs = serialized.get("kwargs", {})
    temp = kwargs.get("temperature")
    if temp is not None:
        try:
            return float(temp)
        except (TypeError, ValueError):
            pass
    return None


def _prompts_to_text(prompts: List[str]) -> str:
    """Join prompt strings into a single text blob for content capture."""
    return "\n---\n".join(prompts)


def _messages_to_text(messages: List[List[Any]]) -> str:
    """Convert LangChain message lists into a human-readable text dump."""
    parts: List[str] = []
    for batch in messages:
        for msg in batch:
            role = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", str(msg))
            parts.append(f"[{role}] {content}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# AgentTelemetryCallback -- sync + async handler
# ---------------------------------------------------------------------------

class AgentTelemetryCallback:
    """LangChain callback handler that emits AgentTelemetry spans and metrics.

    This class implements both the sync and async callback interfaces from
    ``langchain_core.callbacks.BaseCallbackHandler``.  It is constructed
    dynamically inside :meth:`LangChainInstrumentor.instrument` so that
    ``langchain_core`` does not need to be importable at module level.

    The handler keeps an internal mapping from LangChain's ``run_id`` (UUID)
    to active ``AgentSpan`` objects so that the ``*_end`` / ``*_error``
    callbacks can close the correct span.

    Parameters
    ----------
    tracer : AgentTracer
        The tracer instance used to create and finish spans.
    instrumentor : LangChainInstrumentor
        The parent instrumentor, used to access ``_record_llm_metrics``,
        ``_record_tool_metrics``, and ``_capture_content``.
    """

    def __init__(
        self,
        tracer: AgentTracer,
        instrumentor: LangChainInstrumentor,
    ) -> None:
        self._tracer = tracer
        self._instrumentor = instrumentor
        # run_id -> (AgentSpan, start_time_ns)
        self._active_spans: Dict[str, tuple[AgentSpan, int]] = {}

    # -- internal helpers --------------------------------------------------

    def _start_span(
        self,
        run_id: str,
        name: str,
        kind: AgentSpanKind,
        parent_run_id: Optional[str] = None,
        **attrs: Any,
    ) -> AgentSpan:
        """Create a new span and register it under *run_id*."""
        span = self._tracer._make_span(name, kind, **attrs)  # noqa: SLF001

        # If there is a parent run that is still active, reparent.
        if parent_run_id and str(parent_run_id) in self._active_spans:
            parent_span, _ = self._active_spans[str(parent_run_id)]
            span.parent_span_id = parent_span.span_id
            span.trace_id = parent_span.trace_id

        self._tracer._active_spans.append(span)  # noqa: SLF001
        self._active_spans[str(run_id)] = (span, time.time_ns())
        return span

    def _finish_span(
        self,
        run_id: str,
        status: SpanStatus = SpanStatus.OK,
        description: str = "",
    ) -> Optional[AgentSpan]:
        """End the span corresponding to *run_id* and export it."""
        key = str(run_id)
        entry = self._active_spans.pop(key, None)
        if entry is None:
            logger.debug("No active span found for run_id=%s", key)
            return None
        span, _ = entry
        if status != SpanStatus.UNSET:
            span.set_status(status, description)
        self._tracer._finish_span(span)  # noqa: SLF001
        return span

    # ======================================================================
    # LLM callbacks
    # ======================================================================

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM begins generating (non-chat models)."""
        model = _extract_model_name(serialized)
        span = self._start_span(
            str(run_id),
            f"llm.{model}",
            AgentSpanKind.LLM_CALL,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
        )
        span.set_attribute(ATTR_LLM_MODEL, model)
        span.set_attribute(ATTR_LLM_PROVIDER, _extract_provider(serialized))
        temp = _extract_temperature(serialized)
        if temp is not None:
            span.set_attribute(ATTR_LLM_TEMPERATURE, temp)
        span.add_event("llm_start", EventType.LLM_START, model=model)

        if self._instrumentor._capture_content:  # noqa: SLF001
            span.set_attribute(ATTR_LLM_PROMPT, _prompts_to_text(prompts))

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chat model begins generating."""
        model = _extract_model_name(serialized)
        invocation_params = kwargs.get("invocation_params", {})
        # Some versions pass model name via invocation_params
        if model == "unknown":
            for key in ("model_name", "model", "model_id"):
                val = invocation_params.get(key)
                if val:
                    model = str(val)
                    break

        span = self._start_span(
            str(run_id),
            f"llm.{model}",
            AgentSpanKind.LLM_CALL,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
        )
        span.set_attribute(ATTR_LLM_MODEL, model)
        span.set_attribute(ATTR_LLM_PROVIDER, _extract_provider(serialized))
        temp = _extract_temperature(serialized)
        if temp is not None:
            span.set_attribute(ATTR_LLM_TEMPERATURE, temp)
        span.add_event("llm_start", EventType.LLM_START, model=model)

        if self._instrumentor._capture_content:  # noqa: SLF001
            span.set_attribute(ATTR_LLM_PROMPT, _messages_to_text(messages))

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM finishes generating."""
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is None:
            return
        span, start_ns = entry

        # -- Token usage ---------------------------------------------------
        input_tokens = 0
        output_tokens = 0
        llm_output = getattr(response, "llm_output", None) or {}
        token_usage = llm_output.get("token_usage", {})
        if token_usage:
            input_tokens = token_usage.get("prompt_tokens", 0) or 0
            output_tokens = token_usage.get("completion_tokens", 0) or 0
        else:
            # Newer LangChain versions expose usage via response metadata on
            # individual generations.
            for gen_list in getattr(response, "generations", []):
                for gen in gen_list:
                    gen_info = getattr(gen, "generation_info", None) or {}
                    usage = gen_info.get("usage", {}) or gen_info.get("usage_metadata", {})
                    if usage:
                        input_tokens += usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0
                        output_tokens += usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
                    # Also check message response_metadata (ChatModels)
                    msg = getattr(gen, "message", None)
                    if msg is not None:
                        resp_meta = getattr(msg, "response_metadata", None) or {}
                        tok = resp_meta.get("token_usage", {}) or resp_meta.get("usage", {})
                        if tok:
                            input_tokens += tok.get("prompt_tokens", 0) or tok.get("input_tokens", 0) or 0
                            output_tokens += tok.get("completion_tokens", 0) or tok.get("output_tokens", 0) or 0

        total_tokens = input_tokens + output_tokens
        span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
        span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
        span.set_attribute(ATTR_LLM_TOTAL_TOKENS, total_tokens)

        # -- Cost ----------------------------------------------------------
        model = span.attributes.get(ATTR_LLM_MODEL, "unknown")
        cost = estimate_cost(model, input_tokens, output_tokens)
        span.set_attribute(ATTR_LLM_COST_USD, cost)

        # -- Latency -------------------------------------------------------
        latency_ms = (time.time_ns() - start_ns) / 1_000_000
        span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

        # -- Content capture -----------------------------------------------
        if self._instrumentor._capture_content:  # noqa: SLF001
            completions: List[str] = []
            for gen_list in getattr(response, "generations", []):
                for gen in gen_list:
                    text = getattr(gen, "text", None)
                    if text:
                        completions.append(text)
                    else:
                        msg = getattr(gen, "message", None)
                        if msg is not None:
                            completions.append(getattr(msg, "content", str(msg)))
            if completions:
                span.set_attribute(ATTR_LLM_COMPLETION, "\n---\n".join(completions))

        span.add_event(
            "llm_end",
            EventType.LLM_END,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

        # -- Metrics -------------------------------------------------------
        self._instrumentor._record_llm_metrics(  # noqa: SLF001
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )

        self._finish_span(run_id)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call raises an exception."""
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is not None:
            span, _ = entry
            span.add_event("llm_error", EventType.ERROR, error=str(error))
        self._finish_span(run_id, status=SpanStatus.ERROR, description=str(error))

    # ======================================================================
    # Tool callbacks
    # ======================================================================

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool begins execution."""
        tool_name = serialized.get("name", "") or serialized.get("id", ["unknown"])[-1]
        span = self._start_span(
            str(run_id),
            f"tool.{tool_name}",
            AgentSpanKind.TOOL_CALL,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
        )
        span.set_attribute(ATTR_TOOL_NAME, tool_name)
        desc = serialized.get("description", "")
        if desc:
            span.set_attribute("tool.description", desc)
        span.add_event("tool_start", EventType.TOOL_START, tool=tool_name)

        if self._instrumentor._capture_content:  # noqa: SLF001
            span.set_attribute(ATTR_TOOL_INPUT, _safe_serialize(input_str))

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool finishes execution."""
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is None:
            return
        span, start_ns = entry

        latency_ms = (time.time_ns() - start_ns) / 1_000_000
        span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)
        span.set_attribute(ATTR_TOOL_SUCCESS, True)

        if self._instrumentor._capture_content:  # noqa: SLF001
            span.set_attribute(ATTR_TOOL_OUTPUT, _safe_serialize(output))

        tool_name = span.attributes.get(ATTR_TOOL_NAME, "unknown")
        span.add_event("tool_end", EventType.TOOL_END, tool=tool_name)

        self._instrumentor._record_tool_metrics(  # noqa: SLF001
            tool_name=tool_name,
            latency_ms=latency_ms,
            success=True,
        )

        self._finish_span(run_id)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool execution raises an exception."""
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is not None:
            span, start_ns = entry
            latency_ms = (time.time_ns() - start_ns) / 1_000_000
            tool_name = span.attributes.get(ATTR_TOOL_NAME, "unknown")
            span.set_attribute(ATTR_TOOL_SUCCESS, False)
            span.set_attribute(ATTR_TOOL_ERROR, str(error))
            span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)
            span.add_event("tool_error", EventType.ERROR, error=str(error), tool=tool_name)
            self._instrumentor._record_tool_metrics(  # noqa: SLF001
                tool_name=tool_name,
                latency_ms=latency_ms,
                success=False,
            )
        self._finish_span(run_id, status=SpanStatus.ERROR, description=str(error))

    # ======================================================================
    # Chain callbacks
    # ======================================================================

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain begins execution.

        Chains are mapped to TASK spans.  For LangGraph, the outer graph
        invocation appears as a chain, providing a natural root span.
        """
        name_parts: List[str] = serialized.get("id", [])
        chain_name = name_parts[-1] if name_parts else serialized.get("name", "chain")
        span = self._start_span(
            str(run_id),
            f"chain.{chain_name}",
            AgentSpanKind.TASK,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
        )
        span.add_event("chain_start", EventType.AGENT_START, chain=chain_name)

        if self._instrumentor._capture_content:  # noqa: SLF001
            span.set_attribute("chain.input", _safe_serialize(inputs))

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain finishes execution."""
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is not None:
            span, _ = entry
            span.add_event("chain_end", EventType.AGENT_END)
            if self._instrumentor._capture_content:  # noqa: SLF001
                span.set_attribute("chain.output", _safe_serialize(outputs))
        self._finish_span(run_id)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain raises an exception."""
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is not None:
            span, _ = entry
            span.add_event("chain_error", EventType.ERROR, error=str(error))
        self._finish_span(run_id, status=SpanStatus.ERROR, description=str(error))

    # ======================================================================
    # Agent callbacks
    # ======================================================================

    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when an agent selects an action (reasoning step).

        The action object carries ``tool`` (str) and ``tool_input`` fields.
        This represents the agent's *decision* to use a tool, which is a
        reasoning event.  The actual tool execution triggers ``on_tool_start``.
        """
        tool = getattr(action, "tool", "unknown")
        tool_input = getattr(action, "tool_input", "")
        log = getattr(action, "log", "")

        span = self._start_span(
            str(run_id),
            f"agent_action.{tool}",
            AgentSpanKind.REASONING,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
        )
        span.set_attribute("agent.action.tool", tool)
        span.add_event(
            "agent_action",
            EventType.AGENT_MESSAGE,
            tool=tool,
        )

        if self._instrumentor._capture_content:  # noqa: SLF001
            span.set_attribute("agent.action.tool_input", _safe_serialize(tool_input))
            if log:
                span.set_attribute("agent.action.log", _safe_serialize(log))

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when an agent completes its reasoning loop.

        If there is an active span from ``on_agent_action`` for this run_id,
        close it.  Otherwise this is treated as informational.
        """
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is not None:
            span, _ = entry
            return_values = getattr(finish, "return_values", {})
            log = getattr(finish, "log", "")
            span.add_event("agent_finish", EventType.AGENT_END)

            if self._instrumentor._capture_content:  # noqa: SLF001
                if return_values:
                    span.set_attribute("agent.finish.return_values", _safe_serialize(return_values))
                if log:
                    span.set_attribute("agent.finish.log", _safe_serialize(log))

            self._finish_span(run_id)

    # ======================================================================
    # Retry callback (optional, present in newer LangChain)
    # ======================================================================

    def on_retry(
        self,
        retry_state: Any,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a retry is triggered."""
        key = str(run_id)
        entry = self._active_spans.get(key)
        if entry is not None:
            span, _ = entry
            span.add_event(
                "retry",
                EventType.WARNING,
                attempt=getattr(retry_state, "attempt_number", None),
            )

    # ======================================================================
    # Async counterparts
    #
    # The async methods simply delegate to the sync versions.  LangChain's
    # ``AsyncCallbackHandler`` interface mirrors the sync interface -- the
    # default base implementation already calls the sync methods, but we
    # override explicitly so that subclasses of the dynamically-constructed
    # class can rely on deterministic behaviour.
    # ======================================================================

    async def on_llm_start_async(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        self.on_llm_start(serialized, prompts, **kwargs)

    async def on_chat_model_start_async(
        self, serialized: Dict[str, Any], messages: List[List[Any]], **kwargs: Any
    ) -> None:
        self.on_chat_model_start(serialized, messages, **kwargs)

    async def on_llm_end_async(self, response: Any, **kwargs: Any) -> None:
        self.on_llm_end(response, **kwargs)

    async def on_llm_error_async(self, error: BaseException, **kwargs: Any) -> None:
        self.on_llm_error(error, **kwargs)

    async def on_tool_start_async(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        self.on_tool_start(serialized, input_str, **kwargs)

    async def on_tool_end_async(self, output: Any, **kwargs: Any) -> None:
        self.on_tool_end(output, **kwargs)

    async def on_tool_error_async(self, error: BaseException, **kwargs: Any) -> None:
        self.on_tool_error(error, **kwargs)

    async def on_chain_start_async(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        self.on_chain_start(serialized, inputs, **kwargs)

    async def on_chain_end_async(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        self.on_chain_end(outputs, **kwargs)

    async def on_chain_error_async(self, error: BaseException, **kwargs: Any) -> None:
        self.on_chain_error(error, **kwargs)

    async def on_agent_action_async(self, action: Any, **kwargs: Any) -> None:
        self.on_agent_action(action, **kwargs)

    async def on_agent_finish_async(self, finish: Any, **kwargs: Any) -> None:
        self.on_agent_finish(finish, **kwargs)

    async def on_retry_async(self, retry_state: Any, **kwargs: Any) -> None:
        self.on_retry(retry_state, **kwargs)


# ---------------------------------------------------------------------------
# LangChainInstrumentor
# ---------------------------------------------------------------------------

class LangChainInstrumentor(BaseInstrumentor):
    """Instruments LangChain and LangGraph for automatic telemetry capture.

    Injects an :class:`AgentTelemetryCallback` into LangChain's global
    callback manager so that every LLM call, tool invocation, chain
    execution, and agent action is traced without requiring changes to
    user code.

    Parameters
    ----------
    tracer : AgentTracer, optional
        Custom tracer instance.  A default is created if not provided.
    metrics : AgentMetrics, optional
        Custom metrics collector.  A default is created if not provided.
    capture_content : bool
        Whether to capture prompt/completion content and tool I/O.
        Defaults to ``False`` for privacy.

    Example
    -------
    ::

        instrumentor = LangChainInstrumentor(capture_content=True)
        instrumentor.instrument()

        # ... run your LangChain / LangGraph application ...

        spans = instrumentor.tracer.get_spans()
        for s in spans:
            print(s.to_dict())

        instrumentor.uninstrument()
    """

    # The dynamically-created callback handler class (set during instrument())
    _callback_handler_cls: Optional[type] = None
    # The live callback handler instance that was added to LangChain globals
    _callback_instance: Optional[Any] = None

    @property
    def framework_name(self) -> str:
        """Return the name of the framework being instrumented."""
        return "langchain"

    @property
    def callback_handler(self) -> Optional[Any]:
        """Return the active callback handler instance, or ``None``."""
        return self._callback_instance

    # ------------------------------------------------------------------
    # instrument / uninstrument
    # ------------------------------------------------------------------

    def instrument(self) -> None:
        """Install the AgentTelemetry callback into LangChain globals.

        This method:

        1. Imports ``langchain_core`` (fails fast with a clear error if
           the package is not installed).
        2. Dynamically constructs a class that inherits from both
           :class:`AgentTelemetryCallback` and LangChain's
           ``BaseCallbackHandler`` (and ``AsyncCallbackHandler`` when
           available).  This avoids a hard import-time dependency on
           ``langchain_core``.
        3. Instantiates the handler and appends it to
           ``langchain_core.globals.get_openai_callback_manager`` (the
           de-facto global callback list).

        Raises
        ------
        ImportError
            If ``langchain_core`` is not installed.
        RuntimeError
            If instrumentation is already active.
        """
        if self._instrumented:
            logger.warning("LangChain instrumentation is already active.")
            return

        # -- 1. Import langchain_core --------------------------------------
        try:
            from langchain_core.callbacks.base import (
                AsyncCallbackHandler,
                BaseCallbackHandler,
            )
        except ImportError as exc:
            raise ImportError(
                "langchain_core is required for LangChain instrumentation. "
                "Install it with: pip install langchain-core"
            ) from exc

        # -- 2. Build combined handler class --------------------------------
        # We create the class dynamically so that the module can be imported
        # even when langchain_core is not installed (useful for conditional
        # instrumentation).

        _telemetry_ref = AgentTelemetryCallback  # local ref for closure

        class _Handler(BaseCallbackHandler, AsyncCallbackHandler, _telemetry_ref):  # type: ignore[misc]
            """Combined sync + async LangChain callback handler.

            Inherits concrete logic from ``AgentTelemetryCallback`` and
            satisfies LangChain's interface via ``BaseCallbackHandler``
            and ``AsyncCallbackHandler``.
            """

            # Let LangChain know we handle every event type (not selective).
            raise_error = False
            # Unique name for identification in callback lists.
            name = "AgentTelemetryCallback"

            def __init__(self, tracer: AgentTracer, instrumentor: LangChainInstrumentor) -> None:
                # Initialise both base classes explicitly.
                BaseCallbackHandler.__init__(self)
                _telemetry_ref.__init__(self, tracer=tracer, instrumentor=instrumentor)

            # ---- Sync overrides (delegate to AgentTelemetryCallback) -----

            def on_llm_start(self, serialized, prompts, **kw):  # type: ignore[override]
                return _telemetry_ref.on_llm_start(self, serialized, prompts, **kw)

            def on_chat_model_start(self, serialized, messages, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chat_model_start(self, serialized, messages, **kw)

            def on_llm_end(self, response, **kw):  # type: ignore[override]
                return _telemetry_ref.on_llm_end(self, response, **kw)

            def on_llm_error(self, error, **kw):  # type: ignore[override]
                return _telemetry_ref.on_llm_error(self, error, **kw)

            def on_tool_start(self, serialized, input_str, **kw):  # type: ignore[override]
                return _telemetry_ref.on_tool_start(self, serialized, input_str, **kw)

            def on_tool_end(self, output, **kw):  # type: ignore[override]
                return _telemetry_ref.on_tool_end(self, output, **kw)

            def on_tool_error(self, error, **kw):  # type: ignore[override]
                return _telemetry_ref.on_tool_error(self, error, **kw)

            def on_chain_start(self, serialized, inputs, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chain_start(self, serialized, inputs, **kw)

            def on_chain_end(self, outputs, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chain_end(self, outputs, **kw)

            def on_chain_error(self, error, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chain_error(self, error, **kw)

            def on_agent_action(self, action, **kw):  # type: ignore[override]
                return _telemetry_ref.on_agent_action(self, action, **kw)

            def on_agent_finish(self, finish, **kw):  # type: ignore[override]
                return _telemetry_ref.on_agent_finish(self, finish, **kw)

            def on_retry(self, retry_state, **kw):  # type: ignore[override]
                return _telemetry_ref.on_retry(self, retry_state, **kw)

            # ---- Async overrides -----------------------------------------
            # LangChain's AsyncCallbackHandler expects ``a``-prefixed methods
            # (e.g. ``on_llm_start`` is the sync version and the base class
            # routes appropriately). However, for completeness and to ensure
            # async invocations are captured even if the base routing changes,
            # we explicitly wire the ``a*`` variants.

            async def on_llm_start(self, serialized, prompts, **kw):  # type: ignore[override]
                return _telemetry_ref.on_llm_start(self, serialized, prompts, **kw)

            async def on_chat_model_start(self, serialized, messages, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chat_model_start(self, serialized, messages, **kw)

            async def on_llm_end(self, response, **kw):  # type: ignore[override]
                return _telemetry_ref.on_llm_end(self, response, **kw)

            async def on_llm_error(self, error, **kw):  # type: ignore[override]
                return _telemetry_ref.on_llm_error(self, error, **kw)

            async def on_tool_start(self, serialized, input_str, **kw):  # type: ignore[override]
                return _telemetry_ref.on_tool_start(self, serialized, input_str, **kw)

            async def on_tool_end(self, output, **kw):  # type: ignore[override]
                return _telemetry_ref.on_tool_end(self, output, **kw)

            async def on_tool_error(self, error, **kw):  # type: ignore[override]
                return _telemetry_ref.on_tool_error(self, error, **kw)

            async def on_chain_start(self, serialized, inputs, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chain_start(self, serialized, inputs, **kw)

            async def on_chain_end(self, outputs, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chain_end(self, outputs, **kw)

            async def on_chain_error(self, error, **kw):  # type: ignore[override]
                return _telemetry_ref.on_chain_error(self, error, **kw)

            async def on_agent_action(self, action, **kw):  # type: ignore[override]
                return _telemetry_ref.on_agent_action(self, action, **kw)

            async def on_agent_finish(self, finish, **kw):  # type: ignore[override]
                return _telemetry_ref.on_agent_finish(self, finish, **kw)

            async def on_retry(self, retry_state, **kw):  # type: ignore[override]
                return _telemetry_ref.on_retry(self, retry_state, **kw)

        self._callback_handler_cls = _Handler

        # -- 3. Instantiate and register globally --------------------------
        handler = _Handler(tracer=self._tracer, instrumentor=self)
        self._callback_instance = handler

        # Try the recommended approach: configure_callbacks (langchain >=0.1)
        try:
            import langchain_core.globals as lc_globals

            # set_llm_cache / set_verbose are separate; callbacks are managed
            # via the callback_manager module.  The simplest reliable approach
            # is to prepend our handler to the default callbacks list.
            current = getattr(lc_globals, "_default_callbacks", None)
            if current is None:
                # Initialise if not yet set.
                lc_globals._default_callbacks = [handler]  # noqa: SLF001
            else:
                current.append(handler)
        except (ImportError, AttributeError):
            # Fallback for older langchain_core versions: patch
            # CallbackManager.configure to always include our handler.
            pass

        # Also use the public API when available (langchain_core >= 0.2).
        try:
            from langchain_core.callbacks.manager import (
                CallbackManager,
            )
            # Monkey-patch CallbackManager.configure to inject our handler
            # into every callback manager that gets created.
            _orig_configure = CallbackManager.configure

            @classmethod  # type: ignore[misc]
            def _patched_configure(
                cls,
                inheritable_callbacks=None,
                local_callbacks=None,
                verbose=False,
                inheritable_tags=None,
                local_tags=None,
                inheritable_metadata=None,
                local_metadata=None,
            ):
                mgr = _orig_configure.__func__(
                    cls,
                    inheritable_callbacks=inheritable_callbacks,
                    local_callbacks=local_callbacks,
                    verbose=verbose,
                    inheritable_tags=inheritable_tags,
                    local_tags=local_tags,
                    inheritable_metadata=inheritable_metadata,
                    local_metadata=local_metadata,
                )
                # Ensure our handler is present in the callback list.
                handler_present = any(
                    getattr(h, "name", None) == "AgentTelemetryCallback"
                    for h in mgr.handlers
                )
                if not handler_present:
                    mgr.add_handler(handler)
                return mgr

            CallbackManager.configure = _patched_configure  # type: ignore[assignment]
            # Stash original for uninstrument()
            CallbackManager._at_orig_configure = _orig_configure  # type: ignore[attr-defined]  # noqa: SLF001
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch CallbackManager.configure: %s", exc)

        self._instrumented = True
        logger.info("LangChain instrumentation enabled (capture_content=%s).", self._capture_content)

    def uninstrument(self) -> None:
        """Remove the AgentTelemetry callback from LangChain globals.

        After calling this method, no further telemetry will be captured
        from LangChain.  The tracer retains all previously collected spans.
        """
        if not self._instrumented:
            logger.warning("LangChain instrumentation is not active.")
            return

        handler = self._callback_instance

        # Remove from _default_callbacks
        try:
            import langchain_core.globals as lc_globals

            defaults = getattr(lc_globals, "_default_callbacks", None)
            if defaults is not None and handler in defaults:
                defaults.remove(handler)
        except (ImportError, AttributeError):
            pass

        # Restore CallbackManager.configure
        try:
            from langchain_core.callbacks.manager import CallbackManager

            orig = getattr(CallbackManager, "_at_orig_configure", None)
            if orig is not None:
                CallbackManager.configure = orig  # type: ignore[assignment]
                del CallbackManager._at_orig_configure  # type: ignore[attr-defined]
        except (ImportError, AttributeError):
            pass

        # Clear any remaining active spans in the callback handler
        if handler is not None:
            handler._active_spans.clear()  # noqa: SLF001

        self._callback_instance = None
        self._callback_handler_cls = None
        self._instrumented = False
        logger.info("LangChain instrumentation disabled.")
