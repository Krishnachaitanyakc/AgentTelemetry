"""AutoGen (Microsoft) instrumentor for AgentTelemetry.

Monkey-patches AutoGen's core classes to automatically capture telemetry
from multi-agent conversations without requiring user code changes.

Patched targets:
    - ``ConversableAgent.generate_reply``  -- individual agent reasoning steps
    - ``ConversableAgent.send``            -- inter-agent message passing
    - ``ConversableAgent.a_generate_reply`` -- async variant of generate_reply
    - ``ConversableAgent.a_send``          -- async variant of send
    - ``GroupChat.select_speaker``          -- speaker selection in group chats
    - ``ConversableAgent.execute_function_or_tool`` -- tool/function execution
    - ``ConversableAgent.generate_oai_reply`` -- underlying LLM calls

Usage::

    from agenttelemetry.instrumentors.autogen import AutoGenInstrumentor

    instrumentor = AutoGenInstrumentor(capture_content=True)
    instrumentor.instrument()

    # ... run AutoGen agents normally -- telemetry is captured automatically ...

    instrumentor.uninstrument()
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from agenttelemetry.core.events import EventType
from agenttelemetry.core.trace import (
    ATTR_AGENT_NAME,
    ATTR_AGENT_ROLE,
    ATTR_INTERACTION_SOURCE,
    ATTR_INTERACTION_TARGET,
    ATTR_INTERACTION_TYPE,
    ATTR_LLM_COMPLETION,
    ATTR_LLM_COST_USD,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_LATENCY_MS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_TOOL_ERROR,
    ATTR_TOOL_INPUT,
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
# Helpers
# ---------------------------------------------------------------------------

def _safe_str(obj: Any, max_len: int = 4096) -> str:
    """Safely convert an object to a truncated string representation."""
    try:
        text = str(obj)
    except Exception:
        text = "<unserializable>"
    if len(text) > max_len:
        return text[:max_len] + "...<truncated>"
    return text


def _extract_agent_name(agent: Any) -> str:
    """Extract the agent name from an AutoGen agent instance."""
    return getattr(agent, "name", None) or type(agent).__name__


def _extract_model_name(agent: Any) -> str:
    """Best-effort extraction of the LLM model name from an agent's config."""
    # AutoGen stores LLM config in agent.llm_config
    llm_config = getattr(agent, "llm_config", None)
    if not llm_config or not isinstance(llm_config, dict):
        return "unknown"
    # Direct model key
    model = llm_config.get("model")
    if model:
        return str(model)
    # config_list fallback (common AutoGen pattern)
    config_list = llm_config.get("config_list")
    if config_list and isinstance(config_list, (list, tuple)) and len(config_list) > 0:
        first = config_list[0]
        if isinstance(first, dict):
            return str(first.get("model", "unknown"))
    return "unknown"


def _extract_message_content(message: Any) -> Optional[str]:
    """Extract displayable content from an AutoGen message."""
    if message is None:
        return None
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        return message.get("content") or message.get("body") or str(message)
    return str(message)


def _extract_token_usage(response: Any) -> Dict[str, int]:
    """Extract token usage from an OpenAI-style response object."""
    usage: Dict[str, int] = {}
    if response is None:
        return usage

    # AutoGen wraps responses; try common locations
    raw = response
    # ChatCompletion or similar
    if hasattr(raw, "usage"):
        u = raw.usage
        if hasattr(u, "prompt_tokens"):
            usage["input"] = int(u.prompt_tokens)
        if hasattr(u, "completion_tokens"):
            usage["output"] = int(u.completion_tokens)
        if hasattr(u, "total_tokens"):
            usage["total"] = int(u.total_tokens)
    elif isinstance(raw, dict):
        u = raw.get("usage", {})
        if isinstance(u, dict):
            usage["input"] = int(u.get("prompt_tokens", 0))
            usage["output"] = int(u.get("completion_tokens", 0))
            usage["total"] = int(u.get("total_tokens", 0))
    return usage


# ---------------------------------------------------------------------------
# Patch storage dataclass
# ---------------------------------------------------------------------------

class _PatchRecord:
    """Stores the original function reference for a given patch target."""

    __slots__ = ("module", "cls", "attr", "original")

    def __init__(self, module: Any, cls: type, attr: str, original: Callable):
        self.module = module
        self.cls = cls
        self.attr = attr
        self.original = original

    def restore(self) -> None:
        setattr(self.cls, self.attr, self.original)


# ---------------------------------------------------------------------------
# AutoGenInstrumentor
# ---------------------------------------------------------------------------

class AutoGenInstrumentor(BaseInstrumentor):
    """Instruments Microsoft AutoGen for automatic telemetry capture.

    Supports both ``pyautogen`` (>= 0.2) and ``autogen-agentchat`` (>= 0.4)
    package layouts.  The instrumentor detects which package is installed and
    patches accordingly.
    """

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._patches: List[_PatchRecord] = []
        self._autogen_module: Any = None
        self._conversable_cls: Optional[type] = None
        self._groupchat_cls: Optional[type] = None

    # ------------------------------------------------------------------
    # BaseInstrumentor interface
    # ------------------------------------------------------------------

    @property
    def framework_name(self) -> str:
        return "autogen"

    def instrument(self) -> None:
        """Apply monkey-patches to AutoGen classes."""
        if self._instrumented:
            logger.debug("AutoGen instrumentor already active; skipping.")
            return

        self._resolve_autogen_imports()
        self._patch_generate_reply()
        self._patch_a_generate_reply()
        self._patch_send()
        self._patch_a_send()
        self._patch_generate_oai_reply()
        self._patch_execute_function_or_tool()
        self._patch_group_chat_select_speaker()

        self._instrumented = True
        logger.info(
            "AutoGen instrumentation applied (%d patches).", len(self._patches)
        )

    def uninstrument(self) -> None:
        """Remove all monkey-patches and restore original behaviour."""
        if not self._instrumented:
            return
        for patch in reversed(self._patches):
            try:
                patch.restore()
            except Exception:
                logger.warning(
                    "Failed to restore %s.%s",
                    patch.cls.__name__,
                    patch.attr,
                    exc_info=True,
                )
        self._patches.clear()
        self._instrumented = False
        logger.info("AutoGen instrumentation removed.")

    # ------------------------------------------------------------------
    # Import resolution
    # ------------------------------------------------------------------

    def _resolve_autogen_imports(self) -> None:
        """Locate AutoGen classes regardless of package layout.

        Supports:
          - ``autogen`` / ``pyautogen`` (v0.2.x / v0.3.x)
          - ``autogen_agentchat`` (v0.4+)
        """
        conversable_cls = None
        groupchat_cls = None
        autogen_mod = None

        # Strategy 1: Classic pyautogen / autogen namespace
        try:
            import autogen  # type: ignore[import-untyped]

            autogen_mod = autogen
            conversable_cls = getattr(autogen, "ConversableAgent", None)
            groupchat_cls = getattr(autogen, "GroupChat", None)

            # Some builds expose via agentchat sub-package
            if conversable_cls is None:
                try:
                    from autogen.agentchat import ConversableAgent as _CA  # type: ignore
                    conversable_cls = _CA
                except ImportError:
                    pass
            if groupchat_cls is None:
                try:
                    from autogen.agentchat import GroupChat as _GC  # type: ignore
                    groupchat_cls = _GC
                except ImportError:
                    pass
        except ImportError:
            pass

        # Strategy 2: autogen_agentchat (v0.4+ restructured package)
        if conversable_cls is None:
            try:
                import autogen_agentchat  # type: ignore[import-untyped]
                from autogen_agentchat.agents import ConversableAgent as _CA2  # type: ignore

                autogen_mod = autogen_agentchat
                conversable_cls = _CA2
                try:
                    from autogen_agentchat.teams import GroupChat as _GC2  # type: ignore
                    groupchat_cls = _GC2
                except ImportError:
                    pass
            except ImportError:
                pass

        # Strategy 3: pyautogen explicit
        if conversable_cls is None:
            try:
                import pyautogen  # type: ignore[import-untyped]

                autogen_mod = pyautogen
                conversable_cls = getattr(pyautogen, "ConversableAgent", None)
                groupchat_cls = getattr(pyautogen, "GroupChat", None)

                if conversable_cls is None:
                    from pyautogen.agentchat import ConversableAgent as _CA3  # type: ignore
                    conversable_cls = _CA3
                if groupchat_cls is None:
                    try:
                        from pyautogen.agentchat import GroupChat as _GC3  # type: ignore
                        groupchat_cls = _GC3
                    except ImportError:
                        pass
            except ImportError:
                pass

        if conversable_cls is None:
            raise ImportError(
                "AutoGen is not installed. Install it with: "
                "pip install pyautogen  or  pip install autogen-agentchat"
            )

        self._autogen_module = autogen_mod
        self._conversable_cls = conversable_cls
        self._groupchat_cls = groupchat_cls

        # Attempt to record framework version
        version = getattr(autogen_mod, "__version__", "")
        if version:
            self._tracer._framework_version = str(version)

        logger.debug(
            "Resolved AutoGen classes: ConversableAgent=%s, GroupChat=%s, version=%s",
            conversable_cls,
            groupchat_cls,
            version or "<unknown>",
        )

    # ------------------------------------------------------------------
    # Patch helpers
    # ------------------------------------------------------------------

    def _apply_patch(self, cls: type, attr: str, wrapper: Callable) -> None:
        """Replace *cls.attr* with *wrapper*, recording the original."""
        original = getattr(cls, attr, None)
        if original is None:
            logger.debug(
                "Skipping patch: %s.%s does not exist.", cls.__name__, attr
            )
            return
        self._patches.append(
            _PatchRecord(
                module=self._autogen_module,
                cls=cls,
                attr=attr,
                original=original,
            )
        )
        setattr(cls, attr, wrapper)
        logger.debug("Patched %s.%s", cls.__name__, attr)

    # ------------------------------------------------------------------
    # generate_reply  --  REASONING spans
    # ------------------------------------------------------------------

    def _patch_generate_reply(self) -> None:
        cls = self._conversable_cls
        if cls is None:
            return
        original = getattr(cls, "generate_reply", None)
        if original is None:
            return
        instrumentor = self

        @functools.wraps(original)
        def _wrapped_generate_reply(agent_self: Any, *args: Any, **kwargs: Any) -> Any:
            agent_name = _extract_agent_name(agent_self)
            span_name = f"{agent_name}.generate_reply"
            tracer = instrumentor._tracer

            with tracer.start_reasoning(name=span_name) as span:
                span.set_attribute(ATTR_AGENT_NAME, agent_name)
                span.set_attribute(ATTR_AGENT_ROLE, getattr(agent_self, "system_message", "")[:256] if hasattr(agent_self, "system_message") else "")

                # Capture incoming messages if content capture is on
                if instrumentor._capture_content:
                    messages = kwargs.get("messages") or (args[0] if args else None)
                    if messages is not None:
                        span.set_attribute("autogen.input_messages", _safe_str(messages))

                span.add_event("generate_reply_start", EventType.AGENT_START, agent=agent_name)

                try:
                    result = original(agent_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event("generate_reply_error", EventType.ERROR, error=str(exc))
                    instrumentor._metrics.increment("agent.error.count", agent=agent_name)
                    raise

                if instrumentor._capture_content and result is not None:
                    span.set_attribute("autogen.reply", _safe_str(result))

                span.add_event("generate_reply_end", EventType.AGENT_END, agent=agent_name)
                return result

        self._apply_patch(cls, "generate_reply", _wrapped_generate_reply)

    # ------------------------------------------------------------------
    # a_generate_reply  --  async REASONING spans
    # ------------------------------------------------------------------

    def _patch_a_generate_reply(self) -> None:
        cls = self._conversable_cls
        if cls is None:
            return
        original = getattr(cls, "a_generate_reply", None)
        if original is None:
            return
        instrumentor = self

        @functools.wraps(original)
        async def _wrapped_a_generate_reply(agent_self: Any, *args: Any, **kwargs: Any) -> Any:
            agent_name = _extract_agent_name(agent_self)
            span_name = f"{agent_name}.a_generate_reply"
            tracer = instrumentor._tracer

            with tracer.start_reasoning(name=span_name) as span:
                span.set_attribute(ATTR_AGENT_NAME, agent_name)
                span.set_attribute(ATTR_AGENT_ROLE, getattr(agent_self, "system_message", "")[:256] if hasattr(agent_self, "system_message") else "")

                if instrumentor._capture_content:
                    messages = kwargs.get("messages") or (args[0] if args else None)
                    if messages is not None:
                        span.set_attribute("autogen.input_messages", _safe_str(messages))

                span.add_event("a_generate_reply_start", EventType.AGENT_START, agent=agent_name)

                try:
                    result = await original(agent_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event("a_generate_reply_error", EventType.ERROR, error=str(exc))
                    instrumentor._metrics.increment("agent.error.count", agent=agent_name)
                    raise

                if instrumentor._capture_content and result is not None:
                    span.set_attribute("autogen.reply", _safe_str(result))

                span.add_event("a_generate_reply_end", EventType.AGENT_END, agent=agent_name)
                return result

        self._apply_patch(cls, "a_generate_reply", _wrapped_a_generate_reply)

    # ------------------------------------------------------------------
    # send  --  AGENT_COMM spans
    # ------------------------------------------------------------------

    def _patch_send(self) -> None:
        cls = self._conversable_cls
        if cls is None:
            return
        original = getattr(cls, "send", None)
        if original is None:
            return
        instrumentor = self

        @functools.wraps(original)
        def _wrapped_send(agent_self: Any, message: Any, recipient: Any, *args: Any, **kwargs: Any) -> Any:
            source_name = _extract_agent_name(agent_self)
            target_name = _extract_agent_name(recipient)
            tracer = instrumentor._tracer

            # Temporarily override the tracer's agent_name so
            # ATTR_INTERACTION_SOURCE is set correctly.
            old_agent_name = tracer._agent_name
            tracer._agent_name = source_name

            try:
                with tracer.start_agent_comm(target_agent=target_name) as span:
                    span.set_attribute(ATTR_INTERACTION_TYPE, "send")
                    span.set_attribute(ATTR_AGENT_NAME, source_name)

                    if instrumentor._capture_content:
                        content = _extract_message_content(message)
                        if content is not None:
                            span.set_attribute("autogen.message.content", _safe_str(content))

                    # Track request flag -- if request_reply is True the
                    # recipient will generate a reply (creating nested spans).
                    request_reply = kwargs.get("request_reply")
                    if request_reply is not None:
                        span.set_attribute("autogen.request_reply", bool(request_reply))

                    span.add_event(
                        "agent_send",
                        EventType.AGENT_MESSAGE,
                        source=source_name,
                        target=target_name,
                    )

                    instrumentor._metrics.increment(
                        "agent.comm.send.count", source=source_name, target=target_name
                    )

                    try:
                        result = original(agent_self, message, recipient, *args, **kwargs)
                    except Exception as exc:
                        span.set_status(SpanStatus.ERROR, str(exc))
                        span.add_event("agent_send_error", EventType.ERROR, error=str(exc))
                        instrumentor._metrics.increment("agent.error.count", agent=source_name)
                        raise

                    return result
            finally:
                tracer._agent_name = old_agent_name

        self._apply_patch(cls, "send", _wrapped_send)

    # ------------------------------------------------------------------
    # a_send  --  async AGENT_COMM spans
    # ------------------------------------------------------------------

    def _patch_a_send(self) -> None:
        cls = self._conversable_cls
        if cls is None:
            return
        original = getattr(cls, "a_send", None)
        if original is None:
            return
        instrumentor = self

        @functools.wraps(original)
        async def _wrapped_a_send(agent_self: Any, message: Any, recipient: Any, *args: Any, **kwargs: Any) -> Any:
            source_name = _extract_agent_name(agent_self)
            target_name = _extract_agent_name(recipient)
            tracer = instrumentor._tracer

            old_agent_name = tracer._agent_name
            tracer._agent_name = source_name

            try:
                with tracer.start_agent_comm(target_agent=target_name) as span:
                    span.set_attribute(ATTR_INTERACTION_TYPE, "send")
                    span.set_attribute(ATTR_AGENT_NAME, source_name)

                    if instrumentor._capture_content:
                        content = _extract_message_content(message)
                        if content is not None:
                            span.set_attribute("autogen.message.content", _safe_str(content))

                    request_reply = kwargs.get("request_reply")
                    if request_reply is not None:
                        span.set_attribute("autogen.request_reply", bool(request_reply))

                    span.add_event(
                        "agent_a_send",
                        EventType.AGENT_MESSAGE,
                        source=source_name,
                        target=target_name,
                    )

                    instrumentor._metrics.increment(
                        "agent.comm.send.count", source=source_name, target=target_name
                    )

                    try:
                        result = await original(agent_self, message, recipient, *args, **kwargs)
                    except Exception as exc:
                        span.set_status(SpanStatus.ERROR, str(exc))
                        span.add_event("agent_a_send_error", EventType.ERROR, error=str(exc))
                        instrumentor._metrics.increment("agent.error.count", agent=source_name)
                        raise

                    return result
            finally:
                tracer._agent_name = old_agent_name

        self._apply_patch(cls, "a_send", _wrapped_a_send)

    # ------------------------------------------------------------------
    # generate_oai_reply  --  LLM_CALL spans
    # ------------------------------------------------------------------

    def _patch_generate_oai_reply(self) -> None:
        cls = self._conversable_cls
        if cls is None:
            return
        original = getattr(cls, "generate_oai_reply", None)
        if original is None:
            # Some AutoGen versions name it differently; try alternatives
            for alt in ("_generate_oai_reply_from_client", "oai_reply"):
                original = getattr(cls, alt, None)
                if original is not None:
                    break
        if original is None:
            logger.debug("No OAI reply method found on %s; skipping LLM patch.", cls.__name__)
            return

        attr_name = original.__name__ if hasattr(original, "__name__") else "generate_oai_reply"
        instrumentor = self

        @functools.wraps(original)
        def _wrapped_generate_oai_reply(agent_self: Any, *args: Any, **kwargs: Any) -> Any:
            agent_name = _extract_agent_name(agent_self)
            model = _extract_model_name(agent_self)
            tracer = instrumentor._tracer

            with tracer.start_llm_call(model=model) as span:
                span.set_attribute(ATTR_AGENT_NAME, agent_name)

                if instrumentor._capture_content:
                    # Attempt to capture the messages being sent to the LLM
                    messages_arg = kwargs.get("messages") or (args[1] if len(args) > 1 else None)
                    if messages_arg is not None:
                        span.set_attribute(ATTR_LLM_PROMPT, _safe_str(messages_arg))

                span.add_event("llm_call_start", EventType.LLM_START, model=model, agent=agent_name)
                t0 = time.monotonic()

                try:
                    result = original(agent_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.monotonic() - t0) * 1000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event("llm_call_error", EventType.ERROR, error=str(exc))
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    instrumentor._metrics.increment("agent.error.count", agent=agent_name)
                    raise

                latency_ms = (time.monotonic() - t0) * 1000
                span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

                # AutoGen's generate_oai_reply returns (success: bool, response)
                # Extract response for token usage
                response_obj = None
                if isinstance(result, tuple) and len(result) >= 2:
                    response_obj = result[1]
                else:
                    response_obj = result

                # Capture token usage
                usage = _extract_token_usage(response_obj)
                input_tokens = usage.get("input", 0)
                output_tokens = usage.get("output", 0)
                total_tokens = usage.get("total", input_tokens + output_tokens)
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(ATTR_LLM_TOTAL_TOKENS, total_tokens)

                cost = estimate_cost(model, input_tokens, output_tokens)
                if cost > 0:
                    span.set_attribute(ATTR_LLM_COST_USD, cost)

                if instrumentor._capture_content and response_obj is not None:
                    span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(response_obj))

                span.add_event("llm_call_end", EventType.LLM_END, model=model, agent=agent_name)

                instrumentor._record_llm_metrics(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )

                return result

        self._apply_patch(cls, attr_name, _wrapped_generate_oai_reply)

    # ------------------------------------------------------------------
    # execute_function_or_tool  --  TOOL_CALL spans
    # ------------------------------------------------------------------

    def _patch_execute_function_or_tool(self) -> None:
        cls = self._conversable_cls
        if cls is None:
            return

        # AutoGen exposes tool execution through several possible method names
        # depending on version.  We try them in order of likelihood.
        target_attr: Optional[str] = None
        original: Optional[Callable] = None
        for candidate in (
            "execute_function",
            "execute_tool",
            "_execute_tool_call",
            "run_tool",
        ):
            original = getattr(cls, candidate, None)
            if original is not None:
                target_attr = candidate
                break

        if original is None or target_attr is None:
            logger.debug("No tool execution method found on %s; skipping tool patch.", cls.__name__)
            return

        instrumentor = self

        @functools.wraps(original)
        def _wrapped_execute_tool(agent_self: Any, *args: Any, **kwargs: Any) -> Any:
            agent_name = _extract_agent_name(agent_self)
            tracer = instrumentor._tracer

            # Attempt to extract the tool/function name from arguments
            tool_name = "unknown_tool"
            # Common patterns: first arg is a dict with "name", or a
            # function_call dict, or positional func_name
            if args:
                first = args[0]
                if isinstance(first, dict):
                    tool_name = first.get("name", first.get("function", {}).get("name", "unknown_tool"))
                elif isinstance(first, str):
                    tool_name = first
                elif hasattr(first, "name"):
                    tool_name = first.name
                elif hasattr(first, "function") and hasattr(first.function, "name"):
                    tool_name = first.function.name
            tool_name = str(tool_name)

            with tracer.start_tool_call(tool_name=tool_name) as span:
                span.set_attribute(ATTR_AGENT_NAME, agent_name)

                if instrumentor._capture_content and args:
                    span.set_attribute(ATTR_TOOL_INPUT, _safe_str(args))

                span.add_event("tool_call_start", EventType.TOOL_START, tool=tool_name, agent=agent_name)
                t0 = time.monotonic()

                try:
                    result = original(agent_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.monotonic() - t0) * 1000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_TOOL_SUCCESS, False)
                    span.set_attribute(ATTR_TOOL_ERROR, str(exc))
                    span.add_event("tool_call_error", EventType.TOOL_END, tool=tool_name, error=str(exc))
                    instrumentor._record_tool_metrics(tool_name, latency_ms, success=False)
                    raise

                latency_ms = (time.monotonic() - t0) * 1000
                span.set_attribute(ATTR_TOOL_SUCCESS, True)

                if instrumentor._capture_content and result is not None:
                    span.set_attribute(ATTR_TOOL_OUTPUT, _safe_str(result))

                span.add_event("tool_call_end", EventType.TOOL_END, tool=tool_name, agent=agent_name)
                instrumentor._record_tool_metrics(tool_name, latency_ms, success=True)
                return result

        self._apply_patch(cls, target_attr, _wrapped_execute_tool)

    # ------------------------------------------------------------------
    # GroupChat.select_speaker  --  TASK / PLANNING spans
    # ------------------------------------------------------------------

    def _patch_group_chat_select_speaker(self) -> None:
        cls = self._groupchat_cls
        if cls is None:
            logger.debug("GroupChat class not found; skipping group-chat patch.")
            return

        original = getattr(cls, "select_speaker", None)
        if original is None:
            return
        instrumentor = self

        @functools.wraps(original)
        def _wrapped_select_speaker(gc_self: Any, *args: Any, **kwargs: Any) -> Any:
            tracer = instrumentor._tracer

            # Determine the group chat name if available
            gc_name = getattr(gc_self, "name", "group_chat")
            agent_names = []
            agents = getattr(gc_self, "agents", [])
            for a in agents:
                agent_names.append(_extract_agent_name(a))

            with tracer.start_planning(name=f"{gc_name}.select_speaker") as span:
                span.set_attribute(ATTR_AGENT_NAME, gc_name)
                span.set_attribute("autogen.group_chat.agents", agent_names)

                # Last speaker context
                last_speaker = args[0] if args else kwargs.get("last_speaker")
                if last_speaker is not None:
                    span.set_attribute("autogen.group_chat.last_speaker", _extract_agent_name(last_speaker))

                span.add_event(
                    "select_speaker_start",
                    EventType.PLANNING_START,
                    group_chat=gc_name,
                )

                try:
                    selected = original(gc_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event("select_speaker_error", EventType.ERROR, error=str(exc))
                    raise

                selected_name = _extract_agent_name(selected) if selected is not None else "none"
                span.set_attribute("autogen.group_chat.selected_speaker", selected_name)
                span.add_event(
                    "select_speaker_end",
                    EventType.PLANNING_END,
                    selected=selected_name,
                )

                return selected

        self._apply_patch(cls, "select_speaker", _wrapped_select_speaker)

    # ------------------------------------------------------------------
    # High-level conversation wrapper (initiate_chat)
    # ------------------------------------------------------------------

    def wrap_conversation(
        self,
        initiator: Any,
        recipient: Any,
        message: Any,
        **kwargs: Any,
    ) -> Any:
        """Manually wrap an ``initiate_chat`` call in a TASK span.

        While ``send`` / ``generate_reply`` are patched automatically, users
        may want the entire multi-turn conversation grouped under a single
        TASK span.  This helper does exactly that::

            instrumentor = AutoGenInstrumentor(capture_content=True)
            instrumentor.instrument()

            result = instrumentor.wrap_conversation(
                initiator=user_proxy,
                recipient=assistant,
                message="Solve this math problem: ...",
            )
        """
        initiator_name = _extract_agent_name(initiator)
        recipient_name = _extract_agent_name(recipient)
        task_name = f"conversation.{initiator_name}->{recipient_name}"

        with self._tracer.start_task(task_name) as task_span:
            task_span.set_attribute(ATTR_AGENT_NAME, initiator_name)
            task_span.set_attribute(ATTR_INTERACTION_SOURCE, initiator_name)
            task_span.set_attribute(ATTR_INTERACTION_TARGET, recipient_name)

            if self._capture_content:
                content = _extract_message_content(message)
                if content is not None:
                    task_span.set_attribute("autogen.task.initial_message", _safe_str(content))

            task_span.add_event(
                "conversation_start",
                EventType.AGENT_START,
                initiator=initiator_name,
                recipient=recipient_name,
            )

            self._metrics.increment("agent.task.count")

            try:
                result = initiator.initiate_chat(recipient, message=message, **kwargs)
            except Exception as exc:
                task_span.set_status(SpanStatus.ERROR, str(exc))
                task_span.add_event("conversation_error", EventType.ERROR, error=str(exc))
                self._metrics.increment("agent.error.count", agent=initiator_name)
                raise

            task_span.add_event(
                "conversation_end",
                EventType.AGENT_END,
                initiator=initiator_name,
                recipient=recipient_name,
            )

            return result

    async def awrap_conversation(
        self,
        initiator: Any,
        recipient: Any,
        message: Any,
        **kwargs: Any,
    ) -> Any:
        """Async variant of :meth:`wrap_conversation`.

        Wraps ``a_initiate_chat`` in a TASK span::

            result = await instrumentor.awrap_conversation(
                initiator=user_proxy,
                recipient=assistant,
                message="Solve this problem: ...",
            )
        """
        initiator_name = _extract_agent_name(initiator)
        recipient_name = _extract_agent_name(recipient)
        task_name = f"conversation.{initiator_name}->{recipient_name}"

        with self._tracer.start_task(task_name) as task_span:
            task_span.set_attribute(ATTR_AGENT_NAME, initiator_name)
            task_span.set_attribute(ATTR_INTERACTION_SOURCE, initiator_name)
            task_span.set_attribute(ATTR_INTERACTION_TARGET, recipient_name)

            if self._capture_content:
                content = _extract_message_content(message)
                if content is not None:
                    task_span.set_attribute("autogen.task.initial_message", _safe_str(content))

            task_span.add_event(
                "conversation_start",
                EventType.AGENT_START,
                initiator=initiator_name,
                recipient=recipient_name,
            )

            self._metrics.increment("agent.task.count")

            try:
                result = await initiator.a_initiate_chat(recipient, message=message, **kwargs)
            except Exception as exc:
                task_span.set_status(SpanStatus.ERROR, str(exc))
                task_span.add_event("conversation_error", EventType.ERROR, error=str(exc))
                self._metrics.increment("agent.error.count", agent=initiator_name)
                raise

            task_span.add_event(
                "conversation_end",
                EventType.AGENT_END,
                initiator=initiator_name,
                recipient=recipient_name,
            )

            return result
