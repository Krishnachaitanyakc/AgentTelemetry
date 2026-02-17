"""Integration tests for the AutoGen instrumentor.

Uses mock objects to simulate AutoGen's ConversableAgent and GroupChat
classes so tests can run without installing pyautogen / autogen-agentchat.
Exercises instrument/uninstrument, span creation, attribute setting, metric
recording, content capture, and error handling.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock autogen package before importing the instrumentor
# ---------------------------------------------------------------------------

_autogen = types.ModuleType("autogen")
_autogen.__version__ = "0.3.0"
_autogen_agentchat = types.ModuleType("autogen.agentchat")


class _MockConversableAgent:
    """Minimal stand-in for autogen.ConversableAgent."""

    def __init__(self, name="assistant", system_message="You are a helpful assistant.", llm_config=None):
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config or {}

    def generate_reply(self, messages=None, *args, **kwargs):
        return "I can help with that."

    def a_generate_reply(self, messages=None, *args, **kwargs):
        return "async reply"

    def send(self, message, recipient, *args, **kwargs):
        return None

    def a_send(self, message, recipient, *args, **kwargs):
        return None

    def generate_oai_reply(self, client=None, messages=None, *args, **kwargs):
        response = MagicMock()
        response.usage = MagicMock(
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
        )
        return (True, response)

    def execute_function(self, func_call, *args, **kwargs):
        return {"result": "function executed"}

    def initiate_chat(self, recipient, message="", **kwargs):
        return {"chat_history": []}


class _MockGroupChat:
    """Minimal stand-in for autogen.GroupChat."""

    def __init__(self, agents=None, name="test_group"):
        self.agents = agents or []
        self.name = name

    def select_speaker(self, last_speaker=None, *args, **kwargs):
        if self.agents:
            return self.agents[0]
        return None


_autogen.ConversableAgent = _MockConversableAgent
_autogen.GroupChat = _MockGroupChat
_autogen_agentchat.ConversableAgent = _MockConversableAgent
_autogen_agentchat.GroupChat = _MockGroupChat

sys.modules.setdefault("autogen", _autogen)
sys.modules.setdefault("autogen.agentchat", _autogen_agentchat)

from agenttelemetry.core.trace import (  # noqa: E402
    ATTR_AGENT_NAME,
    ATTR_INTERACTION_SOURCE,
    ATTR_INTERACTION_TARGET,
    ATTR_INTERACTION_TYPE,
    ATTR_LLM_COMPLETION,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    AgentSpanKind,
    SpanStatus,
)
from agenttelemetry.instrumentors.autogen import AutoGenInstrumentor  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers to save/restore mock class methods
# ---------------------------------------------------------------------------

_SAVED_GENERATE_REPLY = _MockConversableAgent.generate_reply
_SAVED_SEND = _MockConversableAgent.send
_SAVED_EXECUTE_FUNCTION = _MockConversableAgent.execute_function
_SAVED_GENERATE_OAI_REPLY = _MockConversableAgent.generate_oai_reply
_SAVED_SELECT_SPEAKER = _MockGroupChat.select_speaker


@pytest.fixture(autouse=True)
def restore_mock_methods():
    """Ensure mock class methods are restored after each test."""
    yield
    _MockConversableAgent.generate_reply = _SAVED_GENERATE_REPLY
    _MockConversableAgent.send = _SAVED_SEND
    _MockConversableAgent.execute_function = _SAVED_EXECUTE_FUNCTION
    _MockConversableAgent.generate_oai_reply = _SAVED_GENERATE_OAI_REPLY
    _MockGroupChat.select_speaker = _SAVED_SELECT_SPEAKER


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def instrumentor():
    inst = AutoGenInstrumentor(capture_content=False)
    yield inst
    if inst.is_instrumented:
        inst.uninstrument()


@pytest.fixture()
def instrumentor_with_content():
    inst = AutoGenInstrumentor(capture_content=True)
    yield inst
    if inst.is_instrumented:
        inst.uninstrument()


# ---------------------------------------------------------------------------
# Tests: instrument / uninstrument
# ---------------------------------------------------------------------------

class TestInstrumentUninstrument:
    def test_instrument_sets_flag(self, instrumentor):
        instrumentor.instrument()
        assert instrumentor.is_instrumented is True

    def test_uninstrument_clears_flag(self, instrumentor):
        instrumentor.instrument()
        instrumentor.uninstrument()
        assert instrumentor.is_instrumented is False

    def test_double_instrument_is_noop(self, instrumentor):
        instrumentor.instrument()
        instrumentor.instrument()  # should not raise
        assert instrumentor.is_instrumented is True

    def test_double_uninstrument_is_noop(self, instrumentor):
        instrumentor.instrument()
        instrumentor.uninstrument()
        instrumentor.uninstrument()  # should not raise
        assert instrumentor.is_instrumented is False

    def test_framework_name(self, instrumentor):
        assert instrumentor.framework_name == "autogen"

    def test_uninstrument_restores_methods(self, instrumentor):
        original_generate = _MockConversableAgent.generate_reply
        original_send = _MockConversableAgent.send

        instrumentor.instrument()
        assert _MockConversableAgent.generate_reply is not original_generate
        assert _MockConversableAgent.send is not original_send

        instrumentor.uninstrument()
        assert _MockConversableAgent.generate_reply is original_generate
        assert _MockConversableAgent.send is original_send


# ---------------------------------------------------------------------------
# Tests: generate_reply  (REASONING spans)
# ---------------------------------------------------------------------------

class TestGenerateReply:
    def test_generate_reply_creates_reasoning_span(self, instrumentor):
        instrumentor.instrument()

        agent = _MockConversableAgent(name="helper")
        result = agent.generate_reply(messages=[{"role": "user", "content": "Hi"}])

        assert result == "I can help with that."

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1
        span = reasoning_spans[0]
        assert span.attributes[ATTR_AGENT_NAME] == "helper"
        assert span.status == SpanStatus.OK

    def test_generate_reply_error(self):
        # Swap method BEFORE instrumenting so the wrapper captures the failing version
        def _failing_reply(self, *a, **kw):
            raise RuntimeError("LLM failed")

        _MockConversableAgent.generate_reply = _failing_reply

        inst = AutoGenInstrumentor(capture_content=False)
        inst.instrument()

        agent = _MockConversableAgent(name="failing_agent")
        with pytest.raises(RuntimeError, match="LLM failed"):
            agent.generate_reply()

        spans = inst.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1
        assert reasoning_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()

    def test_generate_reply_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        agent = _MockConversableAgent(name="content_agent")
        agent.generate_reply(messages=[{"role": "user", "content": "Tell me a joke"}])

        spans = inst.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert "autogen.input_messages" in span.attributes
        assert "autogen.reply" in span.attributes

    def test_generate_reply_content_not_captured(self, instrumentor):
        instrumentor.instrument()

        agent = _MockConversableAgent(name="private_agent")
        agent.generate_reply(messages=[{"role": "user", "content": "secret"}])

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert "autogen.input_messages" not in span.attributes
        assert "autogen.reply" not in span.attributes


# ---------------------------------------------------------------------------
# Tests: send  (AGENT_COMM spans)
# ---------------------------------------------------------------------------

class TestSend:
    def test_send_creates_agent_comm_span(self, instrumentor):
        instrumentor.instrument()

        sender = _MockConversableAgent(name="user_proxy")
        recipient = _MockConversableAgent(name="assistant")
        sender.send("Hello assistant", recipient)

        spans = instrumentor.tracer.get_spans()
        comm_spans = [s for s in spans if s.kind == AgentSpanKind.AGENT_COMM]
        assert len(comm_spans) >= 1
        span = comm_spans[0]
        assert span.attributes[ATTR_AGENT_NAME] == "user_proxy"
        assert span.attributes[ATTR_INTERACTION_TYPE] == "send"

    def test_send_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        sender = _MockConversableAgent(name="sender")
        recipient = _MockConversableAgent(name="receiver")
        sender.send("confidential message", recipient)

        spans = inst.tracer.get_spans()
        comm_spans = [s for s in spans if s.kind == AgentSpanKind.AGENT_COMM]
        span = comm_spans[0]
        assert "autogen.message.content" in span.attributes
        assert "confidential message" in span.attributes["autogen.message.content"]

    def test_send_content_not_captured(self, instrumentor):
        instrumentor.instrument()

        sender = _MockConversableAgent(name="sender")
        recipient = _MockConversableAgent(name="receiver")
        sender.send("secret", recipient)

        spans = instrumentor.tracer.get_spans()
        comm_spans = [s for s in spans if s.kind == AgentSpanKind.AGENT_COMM]
        span = comm_spans[0]
        assert "autogen.message.content" not in span.attributes

    def test_send_error(self):
        def _failing_send(self, msg, recipient, *a, **kw):
            raise ConnectionError("network error")

        _MockConversableAgent.send = _failing_send

        inst = AutoGenInstrumentor(capture_content=False)
        inst.instrument()

        sender = _MockConversableAgent(name="sender")
        recipient = _MockConversableAgent(name="receiver")
        with pytest.raises(ConnectionError, match="network error"):
            sender.send("msg", recipient)

        spans = inst.tracer.get_spans()
        comm_spans = [s for s in spans if s.kind == AgentSpanKind.AGENT_COMM]
        assert len(comm_spans) >= 1
        assert comm_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()

    def test_send_metrics(self, instrumentor):
        instrumentor.instrument()

        sender = _MockConversableAgent(name="sender")
        recipient = _MockConversableAgent(name="receiver")
        sender.send("msg", recipient)

        assert instrumentor.metrics.get_counter(
            "agent.comm.send.count", source="sender", target="receiver"
        ) == 1


# ---------------------------------------------------------------------------
# Tests: generate_oai_reply  (LLM_CALL spans)
# ---------------------------------------------------------------------------

class TestGenerateOaiReply:
    def test_oai_reply_creates_llm_span(self, instrumentor):
        instrumentor.instrument()

        agent = _MockConversableAgent(
            name="llm_agent",
            llm_config={"model": "gpt-4o"},
        )
        result = agent.generate_oai_reply()

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        assert len(llm_spans) == 1
        span = llm_spans[0]
        assert span.attributes[ATTR_LLM_MODEL] == "gpt-4o"
        assert span.attributes[ATTR_AGENT_NAME] == "llm_agent"

    def test_oai_reply_token_usage(self, instrumentor):
        instrumentor.instrument()

        agent = _MockConversableAgent(
            name="token_agent",
            llm_config={"model": "gpt-4o"},
        )
        agent.generate_oai_reply()

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert span.attributes[ATTR_LLM_INPUT_TOKENS] == 50
        assert span.attributes[ATTR_LLM_OUTPUT_TOKENS] == 25

    def test_oai_reply_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        agent = _MockConversableAgent(
            name="content_llm_agent",
            llm_config={"model": "gpt-4o"},
        )
        agent.generate_oai_reply(messages=[{"role": "user", "content": "Explain AI"}])

        spans = inst.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert ATTR_LLM_PROMPT in span.attributes
        assert ATTR_LLM_COMPLETION in span.attributes

    def test_oai_reply_metrics(self, instrumentor):
        instrumentor.instrument()

        agent = _MockConversableAgent(
            name="metric_agent",
            llm_config={"model": "gpt-4o"},
        )
        agent.generate_oai_reply()

        assert instrumentor.metrics.get_counter("agent.llm.call.count", model="gpt-4o") == 1
        assert instrumentor.metrics.get_counter("agent.llm.tokens.input", model="gpt-4o") == 50
        assert instrumentor.metrics.get_counter("agent.llm.tokens.output", model="gpt-4o") == 25


# ---------------------------------------------------------------------------
# Tests: execute_function  (TOOL_CALL spans)
# ---------------------------------------------------------------------------

class TestExecuteFunction:
    def test_execute_function_creates_tool_span(self, instrumentor):
        instrumentor.instrument()

        agent = _MockConversableAgent(name="tool_agent")
        func_call = {"name": "calculator", "arguments": '{"a": 1, "b": 2}'}
        agent.execute_function(func_call)

        spans = instrumentor.tracer.get_spans()
        tool_spans = [s for s in spans if s.kind == AgentSpanKind.TOOL_CALL]
        assert len(tool_spans) == 1
        span = tool_spans[0]
        assert span.attributes[ATTR_TOOL_NAME] == "calculator"
        assert span.attributes[ATTR_TOOL_SUCCESS] is True

    def test_execute_function_error(self):
        def _failing_exec(self, *a, **kw):
            raise RuntimeError("tool crashed")

        _MockConversableAgent.execute_function = _failing_exec

        inst = AutoGenInstrumentor(capture_content=False)
        inst.instrument()

        agent = _MockConversableAgent(name="tool_fail_agent")
        with pytest.raises(RuntimeError, match="tool crashed"):
            agent.execute_function({"name": "broken_tool"})

        spans = inst.tracer.get_spans()
        tool_spans = [s for s in spans if s.kind == AgentSpanKind.TOOL_CALL]
        assert len(tool_spans) >= 1
        assert tool_spans[0].status == SpanStatus.ERROR
        assert tool_spans[0].attributes[ATTR_TOOL_SUCCESS] is False

        inst.uninstrument()

    def test_execute_function_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        agent = _MockConversableAgent(name="content_tool_agent")
        agent.execute_function({"name": "search", "arguments": "query"})

        spans = inst.tracer.get_spans()
        tool_spans = [s for s in spans if s.kind == AgentSpanKind.TOOL_CALL]
        span = tool_spans[0]
        assert ATTR_TOOL_INPUT in span.attributes
        assert ATTR_TOOL_OUTPUT in span.attributes

    def test_execute_function_metrics(self, instrumentor):
        instrumentor.instrument()

        agent = _MockConversableAgent(name="metric_tool_agent")
        agent.execute_function({"name": "web_search"})

        assert instrumentor.metrics.get_counter("agent.tool.call.count", tool="web_search") == 1


# ---------------------------------------------------------------------------
# Tests: GroupChat.select_speaker  (PLANNING spans)
# ---------------------------------------------------------------------------

class TestGroupChatSelectSpeaker:
    def test_select_speaker_creates_planning_span(self, instrumentor):
        instrumentor.instrument()

        agent1 = _MockConversableAgent(name="agent_a")
        agent2 = _MockConversableAgent(name="agent_b")
        gc = _MockGroupChat(agents=[agent1, agent2], name="debate")
        selected = gc.select_speaker(last_speaker=agent1)

        spans = instrumentor.tracer.get_spans()
        planning_spans = [s for s in spans if s.kind == AgentSpanKind.PLANNING]
        assert len(planning_spans) >= 1
        span = planning_spans[0]
        assert "autogen.group_chat.selected_speaker" in span.attributes

    def test_select_speaker_error(self):
        def _failing_select(self, *a, **kw):
            raise RuntimeError("selection failed")

        _MockGroupChat.select_speaker = _failing_select

        inst = AutoGenInstrumentor(capture_content=False)
        inst.instrument()

        gc = _MockGroupChat(agents=[], name="broken_gc")
        with pytest.raises(RuntimeError, match="selection failed"):
            gc.select_speaker()

        spans = inst.tracer.get_spans()
        planning_spans = [s for s in spans if s.kind == AgentSpanKind.PLANNING]
        assert len(planning_spans) >= 1
        assert planning_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()


# ---------------------------------------------------------------------------
# Tests: wrap_conversation  (TASK spans)
# ---------------------------------------------------------------------------

class TestWrapConversation:
    def test_wrap_conversation_creates_task_span(self, instrumentor):
        instrumentor.instrument()

        initiator = _MockConversableAgent(name="user_proxy")
        recipient = _MockConversableAgent(name="assistant")
        result = instrumentor.wrap_conversation(
            initiator=initiator,
            recipient=recipient,
            message="Solve x+1=2",
        )

        spans = instrumentor.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        assert len(task_spans) >= 1
        span = task_spans[0]
        assert span.attributes[ATTR_AGENT_NAME] == "user_proxy"
        assert span.attributes[ATTR_INTERACTION_SOURCE] == "user_proxy"
        assert span.attributes[ATTR_INTERACTION_TARGET] == "assistant"

    def test_wrap_conversation_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        initiator = _MockConversableAgent(name="user")
        recipient = _MockConversableAgent(name="bot")
        inst.wrap_conversation(
            initiator=initiator,
            recipient=recipient,
            message="What is 2+2?",
        )

        spans = inst.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        span = task_spans[0]
        assert "autogen.task.initial_message" in span.attributes
