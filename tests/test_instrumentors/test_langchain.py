"""Integration tests for the LangChain instrumentor.

Uses mock objects to simulate LangChain's callback system so tests can run
without installing langchain-core.  Exercises instrument/uninstrument,
span creation, attribute setting, metric recording, content capture, and
error handling.

The dynamically created _Handler inside LangChainInstrumentor has both
sync and async method definitions which conflict in Python MRO.  Therefore,
these tests exercise the core AgentTelemetryCallback class directly (which
contains all the real logic) and test instrument/uninstrument via the
instrumentor API.
"""

from __future__ import annotations

import sys
import types
import uuid
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock langchain_core before importing the instrumentor
# ---------------------------------------------------------------------------

_lc_core = types.ModuleType("langchain_core")
_lc_callbacks = types.ModuleType("langchain_core.callbacks")
_lc_callbacks_base = types.ModuleType("langchain_core.callbacks.base")
_lc_callbacks_manager = types.ModuleType("langchain_core.callbacks.manager")
_lc_globals = types.ModuleType("langchain_core.globals")


class _MockBaseCallbackHandler:
    """Stand-in for langchain_core.callbacks.base.BaseCallbackHandler."""
    def __init__(self, *args, **kwargs):
        pass


class _MockAsyncCallbackHandler:
    """Stand-in for langchain_core.callbacks.base.AsyncCallbackHandler."""
    def __init__(self, *args, **kwargs):
        pass


class _MockCallbackManager:
    """Stand-in for langchain_core.callbacks.manager.CallbackManager."""
    handlers: list = []

    def __init__(self):
        self.handlers = []

    def add_handler(self, handler):
        self.handlers.append(handler)

    @classmethod
    def configure(cls, inheritable_callbacks=None, local_callbacks=None,
                  verbose=False, inheritable_tags=None, local_tags=None,
                  inheritable_metadata=None, local_metadata=None):
        mgr = cls()
        return mgr


_lc_callbacks_base.BaseCallbackHandler = _MockBaseCallbackHandler
_lc_callbacks_base.AsyncCallbackHandler = _MockAsyncCallbackHandler
_lc_callbacks_manager.CallbackManager = _MockCallbackManager
_lc_callbacks.base = _lc_callbacks_base
_lc_callbacks.manager = _lc_callbacks_manager
_lc_core.callbacks = _lc_callbacks
_lc_core.globals = _lc_globals
_lc_globals._default_callbacks = None

sys.modules.setdefault("langchain_core", _lc_core)
sys.modules.setdefault("langchain_core.callbacks", _lc_callbacks)
sys.modules.setdefault("langchain_core.callbacks.base", _lc_callbacks_base)
sys.modules.setdefault("langchain_core.callbacks.manager", _lc_callbacks_manager)
sys.modules.setdefault("langchain_core.globals", _lc_globals)

from agenttelemetry.core.trace import (  # noqa: E402
    ATTR_LLM_COMPLETION,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_LLM_PROVIDER,
    ATTR_LLM_TEMPERATURE,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    AgentSpanKind,
    AgentTracer,
    SpanStatus,
)
from agenttelemetry.instrumentors.langchain import (  # noqa: E402
    AgentTelemetryCallback,
    LangChainInstrumentor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def instrumentor():
    """Return a fresh LangChainInstrumentor with content capture disabled."""
    inst = LangChainInstrumentor(capture_content=False)
    yield inst
    if inst.is_instrumented:
        inst.uninstrument()


@pytest.fixture()
def instrumentor_with_content():
    """Return a fresh LangChainInstrumentor with content capture enabled."""
    inst = LangChainInstrumentor(capture_content=True)
    yield inst
    if inst.is_instrumented:
        inst.uninstrument()


@pytest.fixture()
def callback():
    """Return an AgentTelemetryCallback backed by a fresh instrumentor.

    This bypasses the dynamically created _Handler class (which has
    conflicting sync/async methods) and directly tests the core callback
    logic.
    """
    inst = LangChainInstrumentor(capture_content=False)
    cb = AgentTelemetryCallback(tracer=inst.tracer, instrumentor=inst)
    return cb, inst


@pytest.fixture()
def callback_with_content():
    """Return an AgentTelemetryCallback with content capture enabled."""
    inst = LangChainInstrumentor(capture_content=True)
    cb = AgentTelemetryCallback(tracer=inst.tracer, instrumentor=inst)
    return cb, inst


def _run_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Tests: instrument / uninstrument
# ---------------------------------------------------------------------------

class TestInstrumentUninstrument:
    def test_instrument_sets_flag(self, instrumentor):
        instrumentor.instrument()
        assert instrumentor.is_instrumented is True

    def test_instrument_creates_callback(self, instrumentor):
        instrumentor.instrument()
        assert instrumentor.callback_handler is not None

    def test_uninstrument_clears_flag(self, instrumentor):
        instrumentor.instrument()
        instrumentor.uninstrument()
        assert instrumentor.is_instrumented is False

    def test_uninstrument_clears_handler(self, instrumentor):
        instrumentor.instrument()
        instrumentor.uninstrument()
        assert instrumentor.callback_handler is None

    def test_double_instrument_is_noop(self, instrumentor):
        instrumentor.instrument()
        handler1 = instrumentor.callback_handler
        instrumentor.instrument()  # should not raise
        # handler stays the same
        assert instrumentor.callback_handler is handler1

    def test_double_uninstrument_is_noop(self, instrumentor):
        instrumentor.instrument()
        instrumentor.uninstrument()
        instrumentor.uninstrument()  # should not raise
        assert instrumentor.is_instrumented is False

    def test_framework_name(self, instrumentor):
        assert instrumentor.framework_name == "langchain"


# ---------------------------------------------------------------------------
# Tests: LLM spans
# ---------------------------------------------------------------------------

class TestLLMSpans:
    def test_on_llm_start_end_creates_span(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {
            "id": ["langchain", "chat_models", "ChatOpenAI"],
            "kwargs": {"model_name": "gpt-4o", "temperature": 0.7},
        }

        cb.on_llm_start(serialized, ["Hello"], run_id=run_id)

        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 10, "completion_tokens": 20}}
        response.generations = []

        cb.on_llm_end(response, run_id=run_id)

        spans = inst.tracer.get_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.kind == AgentSpanKind.LLM_CALL
        assert span.status == SpanStatus.OK

    def test_llm_span_attributes(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {
            "id": ["langchain", "chat_models", "ChatOpenAI"],
            "kwargs": {"model_name": "gpt-4o", "temperature": 0.7},
        }
        cb.on_llm_start(serialized, ["prompt"], run_id=run_id)

        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 100, "completion_tokens": 50}}
        response.generations = []
        cb.on_llm_end(response, run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert span.attributes[ATTR_LLM_MODEL] == "gpt-4o"
        assert span.attributes[ATTR_LLM_PROVIDER] == "openai"
        assert span.attributes[ATTR_LLM_TEMPERATURE] == 0.7
        assert span.attributes[ATTR_LLM_INPUT_TOKENS] == 100
        assert span.attributes[ATTR_LLM_OUTPUT_TOKENS] == 50
        assert span.attributes[ATTR_LLM_TOTAL_TOKENS] == 150

    def test_on_chat_model_start_creates_span(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {
            "id": ["langchain", "chat_models", "ChatAnthropic"],
            "kwargs": {"model_name": "claude-3-5-sonnet"},
        }
        msg = MagicMock()
        msg.type = "human"
        msg.content = "Hi there"
        cb.on_chat_model_start(serialized, [[msg]], run_id=run_id)

        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 5, "completion_tokens": 10}}
        response.generations = []
        cb.on_llm_end(response, run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert span.kind == AgentSpanKind.LLM_CALL
        assert span.attributes[ATTR_LLM_PROVIDER] == "anthropic"

    def test_on_llm_error_produces_error_status(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {
            "id": ["langchain", "chat_models", "ChatOpenAI"],
            "kwargs": {"model_name": "gpt-4o"},
        }
        cb.on_llm_start(serialized, ["prompt"], run_id=run_id)
        cb.on_llm_error(RuntimeError("API timeout"), run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert span.status == SpanStatus.ERROR
        assert "API timeout" in span.attributes.get("status.description", "")


# ---------------------------------------------------------------------------
# Tests: Tool spans
# ---------------------------------------------------------------------------

class TestToolSpans:
    def test_tool_start_end_creates_span(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {"name": "web_search", "description": "Search the web"}
        cb.on_tool_start(serialized, "query: python", run_id=run_id)
        cb.on_tool_end("result data", run_id=run_id)

        spans = inst.tracer.get_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.kind == AgentSpanKind.TOOL_CALL
        assert span.attributes[ATTR_TOOL_NAME] == "web_search"
        assert span.attributes[ATTR_TOOL_SUCCESS] is True

    def test_tool_error_produces_error_status(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {"name": "calculator"}
        cb.on_tool_start(serialized, "1/0", run_id=run_id)
        cb.on_tool_error(ZeroDivisionError("division by zero"), run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert span.status == SpanStatus.ERROR
        assert span.attributes[ATTR_TOOL_SUCCESS] is False


# ---------------------------------------------------------------------------
# Tests: Chain spans
# ---------------------------------------------------------------------------

class TestChainSpans:
    def test_chain_start_end_creates_task_span(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {"id": ["langchain", "chains", "SequentialChain"]}
        cb.on_chain_start(serialized, {"input": "data"}, run_id=run_id)
        cb.on_chain_end({"output": "result"}, run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert span.kind == AgentSpanKind.TASK
        assert span.status == SpanStatus.OK

    def test_chain_error_produces_error_status(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {"id": ["langchain", "chains", "LLMChain"]}
        cb.on_chain_start(serialized, {"input": "data"}, run_id=run_id)
        cb.on_chain_error(ValueError("bad input"), run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert span.status == SpanStatus.ERROR


# ---------------------------------------------------------------------------
# Tests: Agent action/finish spans
# ---------------------------------------------------------------------------

class TestAgentSpans:
    def test_agent_action_creates_reasoning_span(self, callback):
        cb, inst = callback

        run_id = _run_id()
        action = MagicMock()
        action.tool = "search"
        action.tool_input = "query"
        action.log = "thinking..."

        cb.on_agent_action(action, run_id=run_id)

        # Finish via agent_finish
        finish = MagicMock()
        finish.return_values = {"output": "done"}
        finish.log = "complete"
        cb.on_agent_finish(finish, run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert span.kind == AgentSpanKind.REASONING
        assert span.attributes["agent.action.tool"] == "search"

    def test_parent_child_relationship(self, callback):
        cb, inst = callback

        parent_id = _run_id()
        child_id = _run_id()

        serialized = {"id": ["langchain", "chains", "AgentExecutor"]}
        cb.on_chain_start(serialized, {"input": "x"}, run_id=parent_id)

        llm_serialized = {
            "id": ["langchain", "chat_models", "ChatOpenAI"],
            "kwargs": {"model_name": "gpt-4o"},
        }
        cb.on_llm_start(llm_serialized, ["prompt"], run_id=child_id, parent_run_id=parent_id)

        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 5, "completion_tokens": 5}}
        response.generations = []
        cb.on_llm_end(response, run_id=child_id)
        cb.on_chain_end({"output": "result"}, run_id=parent_id)

        spans = inst.tracer.get_spans()
        assert len(spans) == 2
        child_span = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL][0]
        parent_span = [s for s in spans if s.kind == AgentSpanKind.TASK][0]
        assert child_span.parent_span_id == parent_span.span_id
        assert child_span.trace_id == parent_span.trace_id


# ---------------------------------------------------------------------------
# Tests: Content capture
# ---------------------------------------------------------------------------

class TestContentCapture:
    def test_content_captured_when_enabled(self, callback_with_content):
        cb, inst = callback_with_content

        run_id = _run_id()
        serialized = {
            "id": ["langchain", "chat_models", "ChatOpenAI"],
            "kwargs": {"model_name": "gpt-4o"},
        }
        cb.on_llm_start(serialized, ["What is Python?"], run_id=run_id)

        gen = MagicMock()
        gen.text = "Python is a programming language."
        gen.generation_info = None
        gen.message = None
        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 10, "completion_tokens": 20}}
        response.generations = [[gen]]
        cb.on_llm_end(response, run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert ATTR_LLM_PROMPT in span.attributes
        assert "What is Python?" in span.attributes[ATTR_LLM_PROMPT]
        assert ATTR_LLM_COMPLETION in span.attributes
        assert "Python is a programming language" in span.attributes[ATTR_LLM_COMPLETION]

    def test_content_not_captured_when_disabled(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {
            "id": ["langchain", "chat_models", "ChatOpenAI"],
            "kwargs": {"model_name": "gpt-4o"},
        }
        cb.on_llm_start(serialized, ["secret prompt"], run_id=run_id)

        gen = MagicMock()
        gen.text = "secret response"
        gen.generation_info = None
        gen.message = None
        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 5, "completion_tokens": 5}}
        response.generations = [[gen]]
        cb.on_llm_end(response, run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert ATTR_LLM_PROMPT not in span.attributes
        assert ATTR_LLM_COMPLETION not in span.attributes

    def test_tool_content_captured_when_enabled(self, callback_with_content):
        cb, inst = callback_with_content

        run_id = _run_id()
        serialized = {"name": "calculator"}
        cb.on_tool_start(serialized, "2+2", run_id=run_id)
        cb.on_tool_end("4", run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert ATTR_TOOL_INPUT in span.attributes
        assert ATTR_TOOL_OUTPUT in span.attributes

    def test_tool_content_not_captured_when_disabled(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {"name": "calculator"}
        cb.on_tool_start(serialized, "2+2", run_id=run_id)
        cb.on_tool_end("4", run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert ATTR_TOOL_INPUT not in span.attributes
        assert ATTR_TOOL_OUTPUT not in span.attributes

    def test_chain_content_captured_when_enabled(self, callback_with_content):
        cb, inst = callback_with_content

        run_id = _run_id()
        serialized = {"id": ["langchain", "chains", "LLMChain"]}
        cb.on_chain_start(serialized, {"question": "What is AI?"}, run_id=run_id)
        cb.on_chain_end({"answer": "Artificial Intelligence"}, run_id=run_id)

        span = inst.tracer.get_spans()[0]
        assert "chain.input" in span.attributes
        assert "chain.output" in span.attributes


# ---------------------------------------------------------------------------
# Tests: Metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_llm_metrics_recorded(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {
            "id": ["langchain", "chat_models", "ChatOpenAI"],
            "kwargs": {"model_name": "gpt-4o"},
        }
        cb.on_llm_start(serialized, ["prompt"], run_id=run_id)

        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 100, "completion_tokens": 50}}
        response.generations = []
        cb.on_llm_end(response, run_id=run_id)

        metrics = inst.metrics
        assert metrics.get_counter("agent.llm.call.count", model="gpt-4o") == 1
        assert metrics.get_counter("agent.llm.tokens.input", model="gpt-4o") == 100
        assert metrics.get_counter("agent.llm.tokens.output", model="gpt-4o") == 50

    def test_tool_metrics_recorded(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {"name": "web_search"}
        cb.on_tool_start(serialized, "query", run_id=run_id)
        cb.on_tool_end("result", run_id=run_id)

        metrics = inst.metrics
        assert metrics.get_counter("agent.tool.call.count", tool="web_search") == 1

    def test_tool_error_metrics_recorded(self, callback):
        cb, inst = callback

        run_id = _run_id()
        serialized = {"name": "broken_tool"}
        cb.on_tool_start(serialized, "input", run_id=run_id)
        cb.on_tool_error(RuntimeError("fail"), run_id=run_id)

        metrics = inst.metrics
        assert metrics.get_counter("agent.tool.call.count", tool="broken_tool") == 1
        assert metrics.get_counter("agent.error.count", tool="broken_tool") == 1


# ---------------------------------------------------------------------------
# Tests: Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_extract_provider_google(self):
        from agenttelemetry.instrumentors.langchain import _extract_provider
        assert _extract_provider({"id": ["langchain", "ChatGoogleGenerativeAI"]}) == "google"

    def test_extract_provider_unknown(self):
        from agenttelemetry.instrumentors.langchain import _extract_provider
        assert _extract_provider({"id": ["langchain", "CustomLLM"]}) == "unknown"

    def test_extract_model_name_fallback(self):
        from agenttelemetry.instrumentors.langchain import _extract_model_name
        assert _extract_model_name({"id": ["ChatSomething"], "kwargs": {}}) == "ChatSomething"

    def test_safe_serialize_truncation(self):
        from agenttelemetry.instrumentors.langchain import _safe_serialize
        long_str = "a" * 5000
        result = _safe_serialize(long_str)
        assert len(result) < 5000
        assert result.endswith("...[truncated]")
