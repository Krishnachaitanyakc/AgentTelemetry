"""Claude Agent SDK (Anthropic) instrumentor for AgentTelemetry.

Automatically captures telemetry from the Anthropic Python SDK by
monkey-patching the ``Messages.create`` method (both sync and async)
on the Anthropic client.

Span mapping:

    messages.create()           -> LLM_CALL span
    tool_use content blocks     -> TOOL_CALL child spans
    thinking content blocks     -> REASONING child spans
    streaming responses         -> LLM_CALL span with streamed aggregation

Usage::

    from agenttelemetry.instrumentors.claude_agent import ClaudeAgentInstrumentor

    instrumentor = ClaudeAgentInstrumentor(capture_content=True)
    instrumentor.instrument()

    # ... use the Anthropic client normally — telemetry is captured automatically ...

    instrumentor.uninstrument()
"""

from __future__ import annotations

import functools
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from agenttelemetry.core.events import EventType
from agenttelemetry.core.trace import (
    ATTR_AGENT_TASK,
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
    AgentSpanKind,
    SpanStatus,
    estimate_cost,
)
from agenttelemetry.instrumentors.base import BaseInstrumentor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom attribute keys for Claude/Anthropic-specific metadata
# ---------------------------------------------------------------------------
ATTR_CLAUDE_STOP_REASON = "claude.stop_reason"
ATTR_CLAUDE_STOP_SEQUENCE = "claude.stop_sequence"
ATTR_CLAUDE_MESSAGE_ID = "claude.message_id"
ATTR_CLAUDE_THINKING = "claude.thinking"
ATTR_CLAUDE_TOOL_USE_ID = "claude.tool_use.id"
ATTR_CLAUDE_CACHE_CREATION_TOKENS = "claude.cache_creation_input_tokens"
ATTR_CLAUDE_CACHE_READ_TOKENS = "claude.cache_read_input_tokens"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_str(obj: Any, max_len: int = 4096) -> str:
    """Convert an object to a truncated string, swallowing exceptions."""
    try:
        text = str(obj)
        if len(text) > max_len:
            return text[:max_len] + "...[truncated]"
        return text
    except Exception:
        return "<unserializable>"


def _safe_json(obj: Any, max_len: int = 4096) -> str:
    """Serialize to JSON with truncation, falling back to str()."""
    try:
        text = json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError, OverflowError):
        text = str(obj)
    if len(text) > max_len:
        return text[:max_len] + "...[truncated]"
    return text


def _extract_usage(response: Any) -> Tuple[int, int]:
    """Extract input/output token counts from an Anthropic response.

    The Anthropic SDK returns a ``usage`` object with ``input_tokens``
    and ``output_tokens`` attributes on the response message.

    Returns (input_tokens, output_tokens).
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    input_tokens = getattr(usage, "input_tokens", 0) or 0
    output_tokens = getattr(usage, "output_tokens", 0) or 0
    return int(input_tokens), int(output_tokens)


def _extract_cache_usage(response: Any) -> Tuple[int, int]:
    """Extract cache-related token counts from an Anthropic response.

    Returns (cache_creation_input_tokens, cache_read_input_tokens).
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return int(creation), int(read)


def _messages_to_text(messages: Any) -> str:
    """Convert Anthropic-style messages list to a readable text dump."""
    if not messages:
        return ""
    parts: List[str] = []
    if isinstance(messages, (list, tuple)):
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Content blocks (text, image, tool_use, etc.)
                    block_texts = []
                    for block in content:
                        if isinstance(block, dict):
                            btype = block.get("type", "")
                            if btype == "text":
                                block_texts.append(block.get("text", ""))
                            elif btype == "tool_use":
                                block_texts.append(
                                    f"[tool_use: {block.get('name', '')}]"
                                )
                            elif btype == "tool_result":
                                block_texts.append(
                                    f"[tool_result: {_safe_str(block.get('content', ''), 256)}]"
                                )
                            elif btype == "thinking":
                                block_texts.append("[thinking]")
                            else:
                                block_texts.append(f"[{btype}]")
                        else:
                            block_texts.append(str(block))
                    content = " ".join(block_texts)
                parts.append(f"[{role}] {content}")
            else:
                parts.append(str(msg))
    return "\n".join(parts)


def _extract_content_blocks(response: Any) -> List[Any]:
    """Get the list of content blocks from an Anthropic response."""
    content = getattr(response, "content", None)
    if content is None:
        return []
    if isinstance(content, list):
        return content
    return [content]


def _content_blocks_to_text(content_blocks: List[Any]) -> str:
    """Convert Anthropic content blocks to a readable string."""
    parts: List[str] = []
    for block in content_blocks:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            parts.append(getattr(block, "text", ""))
        elif block_type == "tool_use":
            name = getattr(block, "name", "unknown")
            parts.append(f"[tool_use: {name}]")
        elif block_type == "thinking":
            parts.append("[thinking]")
        else:
            parts.append(f"[{block_type}]")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# ClaudeAgentInstrumentor
# ---------------------------------------------------------------------------


class ClaudeAgentInstrumentor(BaseInstrumentor):
    """Instruments the Anthropic Python SDK to capture execution telemetry.

    Monkey-patches ``anthropic.resources.Messages.create`` (and the async
    counterpart) to automatically record spans and metrics for every
    ``messages.create()`` call, including tool use and extended thinking.

    Parameters
    ----------
    tracer : AgentTracer, optional
        Pre-configured tracer instance.  A default one is created if omitted.
    metrics : AgentMetrics, optional
        Pre-configured metrics collector.  A default one is created if omitted.
    capture_content : bool
        When ``True``, prompts, completions, tool inputs/outputs, and
        thinking content are recorded as span attributes.  Defaults to
        ``False`` for privacy.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._originals: Dict[str, Any] = {}

    @property
    def framework_name(self) -> str:  # noqa: D401
        return "claude_agent"

    # ------------------------------------------------------------------
    # instrument / uninstrument
    # ------------------------------------------------------------------

    def instrument(self) -> None:
        """Apply monkey-patches to the Anthropic SDK."""
        if self._instrumented:
            logger.debug("Claude Agent instrumentor is already active; skipping.")
            return

        try:
            import anthropic
            import anthropic.resources
        except ImportError as exc:
            raise ImportError(
                "The anthropic package is not installed. "
                "Install it with: pip install anthropic"
            ) from exc

        # Record framework version
        anthropic_version = getattr(anthropic, "__version__", "unknown")
        self._tracer._framework_version = anthropic_version

        # --- Sync Messages.create ---
        messages_cls = anthropic.resources.Messages
        self._originals["Messages.create"] = messages_cls.create
        messages_cls.create = self._wrap_messages_create(messages_cls.create)

        # --- Async Messages.create ---
        try:
            async_messages_cls = anthropic.resources.AsyncMessages
            self._originals["AsyncMessages.create"] = async_messages_cls.create
            async_messages_cls.create = self._wrap_async_messages_create(
                async_messages_cls.create
            )
        except AttributeError:
            logger.debug("AsyncMessages not found; skipping async patch.")

        # --- Streaming: Messages.stream (context-manager wrapper) ---
        if hasattr(messages_cls, "stream"):
            self._originals["Messages.stream"] = messages_cls.stream
            messages_cls.stream = self._wrap_messages_stream(messages_cls.stream)

        self._instrumented = True
        logger.info(
            "Claude Agent instrumentor activated (version=%s, capture_content=%s)",
            anthropic_version,
            self._capture_content,
        )

    def uninstrument(self) -> None:
        """Remove all monkey-patches and restore original methods."""
        if not self._instrumented:
            logger.debug("Claude Agent instrumentor is not active; nothing to undo.")
            return

        try:
            import anthropic
            import anthropic.resources
        except ImportError:
            self._instrumented = False
            self._originals.clear()
            return

        # Restore sync Messages.create
        original = self._originals.get("Messages.create")
        if original is not None:
            anthropic.resources.Messages.create = original

        # Restore async Messages.create
        original = self._originals.get("AsyncMessages.create")
        if original is not None:
            try:
                anthropic.resources.AsyncMessages.create = original
            except AttributeError:
                pass

        # Restore Messages.stream
        original = self._originals.get("Messages.stream")
        if original is not None:
            anthropic.resources.Messages.stream = original

        self._originals.clear()
        self._instrumented = False
        logger.info("Claude Agent instrumentor deactivated -- original methods restored.")

    # ------------------------------------------------------------------
    # Response processing (shared by sync/async/stream)
    # ------------------------------------------------------------------

    def _process_response(
        self,
        response: Any,
        span: Any,
        model: str,
        start_ns: int,
        messages: Any,
    ) -> None:
        """Extract telemetry from an Anthropic Message response and
        populate the span with attributes, events, and child spans.
        """
        latency_ms = (time.time_ns() - start_ns) / 1_000_000
        span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

        # Token usage
        input_tokens, output_tokens = _extract_usage(response)
        span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
        span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
        span.set_attribute(ATTR_LLM_TOTAL_TOKENS, input_tokens + output_tokens)

        # Cache usage
        cache_creation, cache_read = _extract_cache_usage(response)
        if cache_creation > 0:
            span.set_attribute(ATTR_CLAUDE_CACHE_CREATION_TOKENS, cache_creation)
        if cache_read > 0:
            span.set_attribute(ATTR_CLAUDE_CACHE_READ_TOKENS, cache_read)

        # Stop reason
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason:
            span.set_attribute(ATTR_CLAUDE_STOP_REASON, str(stop_reason))

        # Stop sequence
        stop_sequence = getattr(response, "stop_sequence", None)
        if stop_sequence:
            span.set_attribute(ATTR_CLAUDE_STOP_SEQUENCE, str(stop_sequence))

        # Message ID
        msg_id = getattr(response, "id", None)
        if msg_id:
            span.set_attribute(ATTR_CLAUDE_MESSAGE_ID, str(msg_id))

        # Actual model used (may differ from requested, e.g. alias resolution)
        actual_model = getattr(response, "model", None)
        if actual_model:
            span.set_attribute(ATTR_LLM_MODEL, str(actual_model))

        # Content capture (completion side)
        content_blocks = _extract_content_blocks(response)
        if self._capture_content and content_blocks:
            span.set_attribute(
                ATTR_LLM_COMPLETION, _content_blocks_to_text(content_blocks)
            )

        span.add_event(
            "llm_end",
            EventType.LLM_END,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Cost estimation and metrics
        cost = estimate_cost(model, input_tokens, output_tokens)
        self._record_llm_metrics(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )

        # --- Child spans for tool_use and thinking blocks ---
        for block in content_blocks:
            block_type = getattr(block, "type", None)

            if block_type == "tool_use":
                tool_name = getattr(block, "name", "unknown")
                tool_id = getattr(block, "id", "")
                tool_input = getattr(block, "input", {})

                with self._tracer.start_tool_call(tool_name=tool_name) as tool_span:
                    tool_span.set_attribute(ATTR_CLAUDE_TOOL_USE_ID, str(tool_id))
                    if self._capture_content:
                        tool_span.set_attribute(
                            ATTR_TOOL_INPUT, _safe_json(tool_input)
                        )
                    tool_span.set_attribute(ATTR_TOOL_SUCCESS, True)
                    tool_span.add_event(
                        "tool_use",
                        EventType.TOOL_START,
                        tool=tool_name,
                        tool_use_id=str(tool_id),
                    )

                self._record_tool_metrics(
                    tool_name=tool_name, latency_ms=0.0, success=True
                )

            elif block_type == "thinking":
                thinking_text = getattr(block, "thinking", "")
                with self._tracer.start_reasoning(
                    name="claude.thinking"
                ) as thinking_span:
                    thinking_span.set_attribute(ATTR_CLAUDE_THINKING, True)
                    if self._capture_content and thinking_text:
                        thinking_span.set_attribute(
                            "claude.thinking.content",
                            _safe_str(thinking_text),
                        )
                    thinking_span.add_event(
                        "thinking",
                        EventType.AGENT_MESSAGE,
                        has_thinking=True,
                    )

    # ------------------------------------------------------------------
    # Wrapper factories
    # ------------------------------------------------------------------

    def _wrap_messages_create(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched sync ``Messages.create`` method."""
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_create(messages_self: Any, *args: Any, **kwargs: Any) -> Any:
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            system_prompt = kwargs.get("system", None)
            temperature = kwargs.get("temperature", None)
            stream = kwargs.get("stream", False)

            # If stream=True, delegate to the streaming handler
            if stream:
                return instrumentor._handle_streaming_create(
                    original_fn, messages_self, model, messages,
                    system_prompt, temperature, args, kwargs,
                )

            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=str(model)) as span:
                span.set_attribute(ATTR_LLM_PROVIDER, "anthropic")

                if temperature is not None:
                    try:
                        span.set_attribute(ATTR_LLM_TEMPERATURE, float(temperature))
                    except (TypeError, ValueError):
                        pass

                # Content capture (prompt side)
                if instrumentor._capture_content:
                    prompt_text = _messages_to_text(messages)
                    if system_prompt:
                        prompt_text = f"[system] {_safe_str(system_prompt)}\n{prompt_text}"
                    span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt_text))

                span.add_event("llm_start", EventType.LLM_START, model=str(model))

                try:
                    response = original_fn(messages_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event("llm_error", EventType.ERROR, error=str(exc))
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="claude_agent"
                    )
                    raise

                instrumentor._process_response(
                    response, span, str(model), start_ns, messages
                )

                return response

        return _patched_create

    def _wrap_async_messages_create(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched async ``AsyncMessages.create`` method."""
        instrumentor = self

        @functools.wraps(original_fn)
        async def _patched_async_create(
            messages_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            system_prompt = kwargs.get("system", None)
            temperature = kwargs.get("temperature", None)
            stream = kwargs.get("stream", False)

            # If stream=True, delegate to async streaming handler
            if stream:
                return await instrumentor._handle_async_streaming_create(
                    original_fn, messages_self, model, messages,
                    system_prompt, temperature, args, kwargs,
                )

            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=str(model)) as span:
                span.set_attribute(ATTR_LLM_PROVIDER, "anthropic")

                if temperature is not None:
                    try:
                        span.set_attribute(ATTR_LLM_TEMPERATURE, float(temperature))
                    except (TypeError, ValueError):
                        pass

                if instrumentor._capture_content:
                    prompt_text = _messages_to_text(messages)
                    if system_prompt:
                        prompt_text = f"[system] {_safe_str(system_prompt)}\n{prompt_text}"
                    span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt_text))

                span.add_event("llm_start", EventType.LLM_START, model=str(model))

                try:
                    response = await original_fn(messages_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event("llm_error", EventType.ERROR, error=str(exc))
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="claude_agent"
                    )
                    raise

                instrumentor._process_response(
                    response, span, str(model), start_ns, messages
                )

                return response

        return _patched_async_create

    def _handle_streaming_create(
        self,
        original_fn: Callable[..., Any],
        messages_self: Any,
        model: str,
        messages: Any,
        system_prompt: Any,
        temperature: Any,
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """Handle stream=True on sync Messages.create.

        Wraps the returned stream iterator to aggregate token usage and
        content blocks from streamed events, then records telemetry when
        the stream completes.
        """
        instrumentor = self
        start_ns = time.time_ns()

        # Start the LLM span (it stays open until the stream is consumed)
        span = instrumentor._tracer._make_span(
            f"llm.{model}", AgentSpanKind.LLM_CALL
        )
        span.set_attribute(ATTR_LLM_MODEL, str(model))
        span.set_attribute(ATTR_LLM_PROVIDER, "anthropic")
        span.set_attribute("claude.streaming", True)
        instrumentor._tracer._active_spans.append(span)

        if temperature is not None:
            try:
                span.set_attribute(ATTR_LLM_TEMPERATURE, float(temperature))
            except (TypeError, ValueError):
                pass

        if instrumentor._capture_content:
            prompt_text = _messages_to_text(messages)
            if system_prompt:
                prompt_text = f"[system] {_safe_str(system_prompt)}\n{prompt_text}"
            span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt_text))

        span.add_event("llm_start", EventType.LLM_START, model=str(model))

        try:
            stream = original_fn(messages_self, *args, **kwargs)
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            span.add_event("llm_error", EventType.ERROR, error=str(exc))
            instrumentor._tracer._finish_span(span)
            instrumentor._metrics.increment(
                "agent.error.count", framework="claude_agent"
            )
            raise

        return _StreamWrapper(
            stream=stream,
            span=span,
            instrumentor=instrumentor,
            model=model,
            start_ns=start_ns,
            messages=messages,
        )

    async def _handle_async_streaming_create(
        self,
        original_fn: Callable[..., Any],
        messages_self: Any,
        model: str,
        messages: Any,
        system_prompt: Any,
        temperature: Any,
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """Handle stream=True on async AsyncMessages.create."""
        start_ns = time.time_ns()

        span = self._tracer._make_span(
            f"llm.{model}", AgentSpanKind.LLM_CALL
        )
        span.set_attribute(ATTR_LLM_MODEL, str(model))
        span.set_attribute(ATTR_LLM_PROVIDER, "anthropic")
        span.set_attribute("claude.streaming", True)
        self._tracer._active_spans.append(span)

        if temperature is not None:
            try:
                span.set_attribute(ATTR_LLM_TEMPERATURE, float(temperature))
            except (TypeError, ValueError):
                pass

        if self._capture_content:
            prompt_text = _messages_to_text(messages)
            if system_prompt:
                prompt_text = f"[system] {_safe_str(system_prompt)}\n{prompt_text}"
            span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt_text))

        span.add_event("llm_start", EventType.LLM_START, model=str(model))

        try:
            stream = await original_fn(messages_self, *args, **kwargs)
        except Exception as exc:
            span.set_status(SpanStatus.ERROR, str(exc))
            span.add_event("llm_error", EventType.ERROR, error=str(exc))
            self._tracer._finish_span(span)
            self._metrics.increment(
                "agent.error.count", framework="claude_agent"
            )
            raise

        return _AsyncStreamWrapper(
            stream=stream,
            span=span,
            instrumentor=self,
            model=model,
            start_ns=start_ns,
            messages=messages,
        )

    def _wrap_messages_stream(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``Messages.stream`` context-manager method.

        ``client.messages.stream()`` returns a context manager that yields
        events.  We wrap it to capture the final ``Message`` response when
        the context manager exits.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_stream(messages_self: Any, *args: Any, **kwargs: Any) -> Any:
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            system_prompt = kwargs.get("system", None)
            temperature = kwargs.get("temperature", None)

            start_ns = time.time_ns()

            # Call the original .stream() to get the context manager
            stream_cm = original_fn(messages_self, *args, **kwargs)

            return _StreamContextManagerWrapper(
                stream_cm=stream_cm,
                instrumentor=instrumentor,
                model=str(model),
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                start_ns=start_ns,
            )

        return _patched_stream


# ---------------------------------------------------------------------------
# Stream wrappers
# ---------------------------------------------------------------------------


class _StreamWrapper:
    """Wraps a sync streaming response to aggregate telemetry.

    Proxies iteration over the stream and records a completed span
    when the stream is fully consumed or an error occurs.
    """

    def __init__(
        self,
        stream: Any,
        span: Any,
        instrumentor: ClaudeAgentInstrumentor,
        model: str,
        start_ns: int,
        messages: Any,
    ) -> None:
        self._stream = stream
        self._span = span
        self._instrumentor = instrumentor
        self._model = model
        self._start_ns = start_ns
        self._messages = messages
        self._finalized = False

    def __iter__(self):
        return self

    def __next__(self):
        try:
            event = next(self._stream)
            # Record stream chunk events
            event_type_name = getattr(event, "type", None)
            if event_type_name:
                self._span.add_event(
                    "stream_chunk",
                    EventType.LLM_STREAM_CHUNK,
                    event_type=str(event_type_name),
                )
            return event
        except StopIteration:
            self._finalize()
            raise
        except Exception as exc:
            self._span.set_status(SpanStatus.ERROR, str(exc))
            self._span.add_event("stream_error", EventType.ERROR, error=str(exc))
            self._finalize()
            raise

    def _finalize(self) -> None:
        """Record final metrics when the stream completes."""
        if self._finalized:
            return
        self._finalized = True

        # Try to get the final message from the stream
        final_message = getattr(self._stream, "get_final_message", None)
        if callable(final_message):
            try:
                response = final_message()
                self._instrumentor._process_response(
                    response, self._span, self._model, self._start_ns,
                    self._messages,
                )
            except Exception:
                pass

        # Finalize the span
        latency_ms = (time.time_ns() - self._start_ns) / 1_000_000
        if ATTR_LLM_LATENCY_MS not in self._span.attributes:
            self._span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
        self._instrumentor._tracer._finish_span(self._span)

    def __enter__(self):
        if hasattr(self._stream, "__enter__"):
            self._stream.__enter__()
        return self

    def __exit__(self, *exc_info):
        self._finalize()
        if hasattr(self._stream, "__exit__"):
            return self._stream.__exit__(*exc_info)
        return False

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying stream."""
        return getattr(self._stream, name)


class _AsyncStreamWrapper:
    """Wraps an async streaming response to aggregate telemetry."""

    def __init__(
        self,
        stream: Any,
        span: Any,
        instrumentor: ClaudeAgentInstrumentor,
        model: str,
        start_ns: int,
        messages: Any,
    ) -> None:
        self._stream = stream
        self._span = span
        self._instrumentor = instrumentor
        self._model = model
        self._start_ns = start_ns
        self._messages = messages
        self._finalized = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            event = await self._stream.__anext__()
            event_type_name = getattr(event, "type", None)
            if event_type_name:
                self._span.add_event(
                    "stream_chunk",
                    EventType.LLM_STREAM_CHUNK,
                    event_type=str(event_type_name),
                )
            return event
        except StopAsyncIteration:
            await self._finalize()
            raise
        except Exception as exc:
            self._span.set_status(SpanStatus.ERROR, str(exc))
            self._span.add_event("stream_error", EventType.ERROR, error=str(exc))
            await self._finalize()
            raise

    async def _finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True

        final_message = getattr(self._stream, "get_final_message", None)
        if callable(final_message):
            try:
                response = await final_message()
                self._instrumentor._process_response(
                    response, self._span, self._model, self._start_ns,
                    self._messages,
                )
            except Exception:
                pass

        latency_ms = (time.time_ns() - self._start_ns) / 1_000_000
        if ATTR_LLM_LATENCY_MS not in self._span.attributes:
            self._span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
        self._instrumentor._tracer._finish_span(self._span)

    async def __aenter__(self):
        if hasattr(self._stream, "__aenter__"):
            await self._stream.__aenter__()
        return self

    async def __aexit__(self, *exc_info):
        await self._finalize()
        if hasattr(self._stream, "__aexit__"):
            return await self._stream.__aexit__(*exc_info)
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class _StreamContextManagerWrapper:
    """Wraps the ``Messages.stream()`` context manager to capture telemetry
    from the final message when the context exits.
    """

    def __init__(
        self,
        stream_cm: Any,
        instrumentor: ClaudeAgentInstrumentor,
        model: str,
        messages: Any,
        system_prompt: Any,
        temperature: Any,
        start_ns: int,
    ) -> None:
        self._stream_cm = stream_cm
        self._instrumentor = instrumentor
        self._model = model
        self._messages = messages
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._start_ns = start_ns
        self._span = None
        self._inner_stream = None

    def __enter__(self):
        self._span = self._instrumentor._tracer._make_span(
            f"llm.{self._model}", AgentSpanKind.LLM_CALL
        )
        self._span.set_attribute(ATTR_LLM_MODEL, self._model)
        self._span.set_attribute(ATTR_LLM_PROVIDER, "anthropic")
        self._span.set_attribute("claude.streaming", True)
        self._instrumentor._tracer._active_spans.append(self._span)

        if self._temperature is not None:
            try:
                self._span.set_attribute(ATTR_LLM_TEMPERATURE, float(self._temperature))
            except (TypeError, ValueError):
                pass

        if self._instrumentor._capture_content:
            prompt_text = _messages_to_text(self._messages)
            if self._system_prompt:
                prompt_text = f"[system] {_safe_str(self._system_prompt)}\n{prompt_text}"
            self._span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt_text))

        self._span.add_event("llm_start", EventType.LLM_START, model=self._model)

        self._inner_stream = self._stream_cm.__enter__()
        return self._inner_stream

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self._span is not None:
            self._span.set_status(SpanStatus.ERROR, str(exc_val))
            self._span.add_event("stream_error", EventType.ERROR, error=str(exc_val))

        # Try to extract the final message from the stream manager
        if self._inner_stream is not None and self._span is not None:
            final_message = getattr(self._inner_stream, "get_final_message", None)
            if callable(final_message):
                try:
                    response = final_message()
                    self._instrumentor._process_response(
                        response, self._span, self._model, self._start_ns,
                        self._messages,
                    )
                except Exception:
                    pass

        result = self._stream_cm.__exit__(exc_type, exc_val, exc_tb)

        if self._span is not None:
            latency_ms = (time.time_ns() - self._start_ns) / 1_000_000
            if ATTR_LLM_LATENCY_MS not in self._span.attributes:
                self._span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
            self._instrumentor._tracer._finish_span(self._span)

        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream_cm, name)
