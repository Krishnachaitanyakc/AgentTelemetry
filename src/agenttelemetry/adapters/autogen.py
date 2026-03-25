"""AutoGen instrumentation adapter.

Monkey-patches autogen_core / autogen_agentchat classes to capture
LLM_CALL and AGENT spans.
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
    TOOL_NAME,
    TOOL_OUTPUT,
    TOOL_STATUS,
    estimate_cost,
)
from agenttelemetry.core.privacy import PrivacyLevel, filter_attributes, should_capture_content


class AutoGenInstrumentor(BaseInstrumentor):
    """Instruments Microsoft AutoGen (autogen-core / autogen-agentchat)."""

    _tracer: Optional[trace.Tracer] = None
    _privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY
    _original_llm_create: Any = None
    _original_agent_run: Any = None
    _patched_module: Optional[str] = None  # Track which module was patched

    def instrumentation_dependencies(self) -> Collection[str]:
        return ("autogen-core >= 0.4.0",)

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider")
        self._privacy_level = kwargs.get("privacy_level", PrivacyLevel.METADATA_ONLY)
        self._tracer = trace.get_tracer(
            "agenttelemetry.autogen", "0.1.0", tracer_provider=tracer_provider
        )

        self._patch_llm_client()
        self._patch_agent_chat()

    def _patch_llm_client(self) -> None:
        """Patch ChatCompletionClient.create() for LLM_CALL spans."""
        # Try autogen-ext first (newer), then autogen-core
        client_class = None
        try:
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            client_class = OpenAIChatCompletionClient
            self._patched_module = "autogen_ext"
        except ImportError:
            try:
                from autogen_core.models import ChatCompletionClient
                client_class = ChatCompletionClient
                self._patched_module = "autogen_core"
            except ImportError:
                # Neither available — skip LLM patching
                return

        if not hasattr(client_class, "create"):
            return

        self._original_llm_create = client_class.create
        instrumentor = self

        async def patched_create(self_client: Any, *args: Any, **kw: Any) -> Any:
            return await instrumentor._traced_llm_create(
                self_client, instrumentor._original_llm_create, *args, **kw
            )

        patched_create.__wrapped__ = self._original_llm_create
        client_class.create = patched_create

    def _patch_agent_chat(self) -> None:
        """Patch agent chat run methods for AGENT spans."""
        try:
            from autogen_agentchat.agents import BaseChatAgent
        except ImportError:
            return

        if not hasattr(BaseChatAgent, "run"):
            # Try on_messages instead
            if hasattr(BaseChatAgent, "on_messages"):
                self._original_agent_run = BaseChatAgent.on_messages
                instrumentor = self

                async def patched_on_messages(self_agent: Any, *args: Any, **kw: Any) -> Any:
                    return await instrumentor._traced_agent_run(
                        self_agent, instrumentor._original_agent_run, *args, **kw
                    )

                patched_on_messages.__wrapped__ = self._original_agent_run
                BaseChatAgent.on_messages = patched_on_messages
            return

        self._original_agent_run = BaseChatAgent.run
        instrumentor = self

        async def patched_run(self_agent: Any, *args: Any, **kw: Any) -> Any:
            return await instrumentor._traced_agent_run(
                self_agent, instrumentor._original_agent_run, *args, **kw
            )

        patched_run.__wrapped__ = self._original_agent_run
        BaseChatAgent.run = patched_run

    def _uninstrument(self, **kwargs: Any) -> None:
        # Restore LLM client
        if self._original_llm_create is not None:
            try:
                if self._patched_module == "autogen_ext":
                    from autogen_ext.models.openai import OpenAIChatCompletionClient
                    OpenAIChatCompletionClient.create = self._original_llm_create
                else:
                    from autogen_core.models import ChatCompletionClient
                    ChatCompletionClient.create = self._original_llm_create
            except ImportError:
                pass
            self._original_llm_create = None

        # Restore agent
        if self._original_agent_run is not None:
            try:
                from autogen_agentchat.agents import BaseChatAgent
                method_name = self._original_agent_run.__name__
                setattr(BaseChatAgent, method_name, self._original_agent_run)
            except (ImportError, AttributeError):
                pass
            self._original_agent_run = None

        self._patched_module = None

    async def _traced_llm_create(
        self, self_client: Any, original: Any, *args: Any, **kwargs: Any
    ) -> Any:
        start = time.perf_counter()

        # Extract model info from client
        model = getattr(self_client, "model", "") or getattr(
            self_client, "_model", ""
        ) or ""

        try:
            response = await original(self_client, *args, **kwargs)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            attrs = filter_attributes(
                {
                    AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
                    LLM_PROVIDER: "autogen",
                    LLM_MODEL: str(model),
                    LLM_LATENCY_MS: latency_ms,
                    AGENT_FRAMEWORK: "autogen",
                },
                self._privacy_level,
            )
            with self._tracer.start_as_current_span(
                "autogen.llm.create",
                kind=trace.SpanKind.INTERNAL,
                attributes=attrs,
            ) as span:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        attrs: Dict[str, Any] = {
            AGENT_SPAN_KIND: AgentSpanKind.LLM_CALL,
            LLM_PROVIDER: "autogen",
            LLM_MODEL: str(model),
            LLM_LATENCY_MS: latency_ms,
            AGENT_FRAMEWORK: "autogen",
        }

        # Extract usage from response
        usage = getattr(response, "usage", None)
        if usage:
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
            attrs[LLM_INPUT_TOKENS] = input_tokens
            attrs[LLM_OUTPUT_TOKENS] = output_tokens
            attrs[LLM_TOTAL_TOKENS] = input_tokens + output_tokens
            attrs[LLM_COST] = estimate_cost(str(model), input_tokens, output_tokens)

        if should_capture_content(self._privacy_level):
            # Extract messages from args
            if args:
                attrs[LLM_PROMPT] = str(args[0])
            elif "messages" in kwargs:
                attrs[LLM_PROMPT] = str(kwargs["messages"])
            # Extract completion
            content = getattr(response, "content", None)
            if content:
                attrs[LLM_COMPLETION] = str(content)

        filtered = filter_attributes(attrs, self._privacy_level)
        with self._tracer.start_as_current_span(
            "autogen.llm.create",
            kind=trace.SpanKind.INTERNAL,
            attributes=filtered,
        ):
            pass

        return response

    async def _traced_agent_run(
        self, self_agent: Any, original: Any, *args: Any, **kwargs: Any
    ) -> Any:
        agent_name = getattr(self_agent, "name", type(self_agent).__name__)
        attrs: Dict[str, Any] = {
            AGENT_SPAN_KIND: AgentSpanKind.AGENT,
            AGENT_FRAMEWORK: "autogen",
            AGENT_NAME: agent_name,
        }
        description = getattr(self_agent, "description", None)
        if description:
            attrs[AGENT_ROLE] = str(description)[:200]

        filtered = filter_attributes(attrs, self._privacy_level)

        start = time.perf_counter()
        with self._tracer.start_as_current_span(
            f"autogen.agent.{agent_name}",
            kind=trace.SpanKind.INTERNAL,
            attributes=filtered,
        ) as span:
            try:
                result = await original(self_agent, *args, **kwargs)
                latency_ms = (time.perf_counter() - start) * 1000
                span.set_attribute(LLM_LATENCY_MS, latency_ms)
                return result
            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                span.set_attribute(LLM_LATENCY_MS, latency_ms)
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
