"""Integration tests for the CrewAI instrumentor.

Uses mock objects to simulate CrewAI classes so tests can run without
installing the crewai package.  Exercises instrument/uninstrument, span
creation, attribute setting, metric recording, content capture, delegation
detection, and error handling.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock crewai package before importing the instrumentor
# ---------------------------------------------------------------------------

_crewai = types.ModuleType("crewai")
_crewai.__version__ = "0.40.0"
_crewai_llm = types.ModuleType("crewai.llm")


class _MockAgent:
    """Minimal stand-in for crewai.Agent."""
    def __init__(self, role="researcher", goal="research", backstory="expert", llm=None):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm = llm

    def execute_task(self, task, *args, **kwargs):
        return "task result"


class _MockTask:
    """Minimal stand-in for crewai.Task."""
    def __init__(self, description="a task", expected_output="output", agent=None):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.context = None

    def execute(self, *args, **kwargs):
        return "task output"


class _MockCrew:
    """Minimal stand-in for crewai.Crew."""
    def __init__(self, agents=None, tasks=None, process="sequential", name="test_crew"):
        self.agents = agents or []
        self.tasks = tasks or []
        self.process = process
        self.name = name

    def kickoff(self, *args, **kwargs):
        return "crew result"


class _MockLLM:
    """Minimal stand-in for crewai.llm.LLM."""
    def __init__(self, model="gpt-4o"):
        self.model = model

    def call(self, messages, *args, **kwargs):
        return MagicMock(
            usage=MagicMock(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            ),
            choices=[
                MagicMock(message=MagicMock(content="LLM response"))
            ],
        )


_crewai.Agent = _MockAgent
_crewai.Task = _MockTask
_crewai.Crew = _MockCrew
_crewai_llm.LLM = _MockLLM

sys.modules.setdefault("crewai", _crewai)
sys.modules.setdefault("crewai.llm", _crewai_llm)

from agenttelemetry.core.trace import (  # noqa: E402
    ATTR_AGENT_NAME,
    ATTR_AGENT_ROLE,
    ATTR_LLM_COMPLETION,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    AgentSpanKind,
    SpanStatus,
)
from agenttelemetry.instrumentors.crewai import (  # noqa: E402
    ATTR_CREW_NAME,
    ATTR_CREW_NUM_AGENTS,
    ATTR_CREW_NUM_TASKS,
    ATTR_CREW_PROCESS,
    ATTR_TASK_DESCRIPTION,
    CrewAIInstrumentor,
)


# ---------------------------------------------------------------------------
# Save originals for restoration
# ---------------------------------------------------------------------------

_SAVED_KICKOFF = _MockCrew.kickoff
_SAVED_EXECUTE_TASK = _MockAgent.execute_task
_SAVED_TASK_EXECUTE = _MockTask.execute
_SAVED_LLM_CALL = _MockLLM.call


@pytest.fixture(autouse=True)
def restore_mock_methods():
    """Ensure mock class methods are restored after each test."""
    yield
    _MockCrew.kickoff = _SAVED_KICKOFF
    _MockAgent.execute_task = _SAVED_EXECUTE_TASK
    _MockTask.execute = _SAVED_TASK_EXECUTE
    _MockLLM.call = _SAVED_LLM_CALL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def instrumentor():
    inst = CrewAIInstrumentor(capture_content=False)
    yield inst
    if inst.is_instrumented:
        inst.uninstrument()


@pytest.fixture()
def instrumentor_with_content():
    inst = CrewAIInstrumentor(capture_content=True)
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
        assert instrumentor.framework_name == "crewai"

    def test_uninstrument_restores_originals(self, instrumentor):
        original_kickoff = _MockCrew.kickoff
        original_execute_task = _MockAgent.execute_task
        original_task_execute = _MockTask.execute

        instrumentor.instrument()
        assert _MockCrew.kickoff is not original_kickoff
        assert _MockAgent.execute_task is not original_execute_task
        assert _MockTask.execute is not original_task_execute

        instrumentor.uninstrument()
        assert _MockCrew.kickoff is original_kickoff
        assert _MockAgent.execute_task is original_execute_task
        assert _MockTask.execute is original_task_execute


# ---------------------------------------------------------------------------
# Tests: Crew.kickoff spans (TASK)
# ---------------------------------------------------------------------------

class TestCrewKickoff:
    def test_kickoff_creates_task_span(self, instrumentor):
        instrumentor.instrument()

        agent = _MockAgent(role="writer")
        task = _MockTask(description="Write an essay", agent=agent)
        crew = _MockCrew(agents=[agent], tasks=[task], name="writing_crew")
        crew.kickoff()

        spans = instrumentor.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        assert len(task_spans) >= 1
        span = task_spans[0]
        assert span.status == SpanStatus.OK

    def test_kickoff_span_attributes(self, instrumentor):
        instrumentor.instrument()

        agent1 = _MockAgent(role="researcher")
        agent2 = _MockAgent(role="writer")
        task = _MockTask(description="Research topic", agent=agent1)
        crew = _MockCrew(agents=[agent1, agent2], tasks=[task], name="team")
        crew.kickoff()

        spans = instrumentor.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        span = task_spans[0]
        assert span.attributes[ATTR_CREW_NAME] == "team"
        assert span.attributes[ATTR_CREW_PROCESS] == "sequential"
        assert span.attributes[ATTR_CREW_NUM_AGENTS] == 2
        assert span.attributes[ATTR_CREW_NUM_TASKS] == 1

    def test_kickoff_error_produces_error_span(self):
        # Swap method BEFORE instrumenting
        def _failing_kickoff(self, *a, **kw):
            raise RuntimeError("crew failed")

        _MockCrew.kickoff = _failing_kickoff

        inst = CrewAIInstrumentor(capture_content=False)
        inst.instrument()

        crew = _MockCrew(name="failing_crew")
        with pytest.raises(RuntimeError, match="crew failed"):
            crew.kickoff()

        spans = inst.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        assert len(task_spans) >= 1
        assert task_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()

    def test_kickoff_content_captured_when_enabled(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        crew = _MockCrew(name="content_crew", agents=[], tasks=[])
        crew.kickoff()

        spans = inst.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        span = task_spans[0]
        assert "crewai.crew.result" in span.attributes


# ---------------------------------------------------------------------------
# Tests: Agent.execute_task spans (REASONING)
# ---------------------------------------------------------------------------

class TestAgentExecuteTask:
    def test_execute_task_creates_reasoning_span(self, instrumentor):
        instrumentor.instrument()

        agent = _MockAgent(role="analyst", goal="analyze data")
        task = _MockTask(description="Analyze the dataset", agent=agent)
        agent.execute_task(task)

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1

    def test_execute_task_span_attributes(self, instrumentor):
        instrumentor.instrument()

        agent = _MockAgent(role="analyst", goal="analyze")
        task = _MockTask(description="Analyze data", agent=agent)
        agent.execute_task(task)

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert span.attributes[ATTR_AGENT_NAME] == "analyst"
        assert span.attributes[ATTR_AGENT_ROLE] == "analyst"

    def test_execute_task_error_produces_error_span(self):
        def _failing_execute(self, *a, **kw):
            raise ValueError("bad task")

        _MockAgent.execute_task = _failing_execute

        inst = CrewAIInstrumentor(capture_content=False)
        inst.instrument()

        agent = _MockAgent(role="failing_agent")
        task = _MockTask(description="fail", agent=agent)
        with pytest.raises(ValueError, match="bad task"):
            agent.execute_task(task)

        spans = inst.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1
        assert reasoning_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()

    def test_execute_task_content_captured_when_enabled(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        agent = _MockAgent(role="content_agent")
        task = _MockTask(description="Describe AI trends", agent=agent)
        agent.execute_task(task)

        spans = inst.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert ATTR_TASK_DESCRIPTION in span.attributes

    def test_execute_task_content_not_captured_when_disabled(self, instrumentor):
        instrumentor.instrument()

        agent = _MockAgent(role="private_agent")
        task = _MockTask(description="Secret task", agent=agent)
        agent.execute_task(task)

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert ATTR_TASK_DESCRIPTION not in span.attributes


# ---------------------------------------------------------------------------
# Tests: Task.execute spans
# ---------------------------------------------------------------------------

class TestTaskExecute:
    def test_task_execute_creates_span(self, instrumentor):
        instrumentor.instrument()

        agent = _MockAgent(role="executor")
        task = _MockTask(description="Execute something", agent=agent)
        task.execute()

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1


# ---------------------------------------------------------------------------
# Tests: LLM call spans
# ---------------------------------------------------------------------------

class TestLLMCallSpans:
    def test_llm_call_creates_span(self, instrumentor):
        instrumentor.instrument()

        llm = _MockLLM(model="gpt-4o")
        llm.call([{"role": "user", "content": "Hello"}])

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        assert len(llm_spans) == 1

    def test_llm_call_attributes(self, instrumentor):
        instrumentor.instrument()

        llm = _MockLLM(model="gpt-4o")
        llm.call([{"role": "user", "content": "Hello"}])

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert span.attributes[ATTR_LLM_MODEL] == "gpt-4o"

    def test_llm_call_content_captured_when_enabled(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        llm = _MockLLM(model="gpt-4o")
        llm.call([{"role": "user", "content": "Hello"}])

        spans = inst.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert ATTR_LLM_PROMPT in span.attributes
        assert ATTR_LLM_COMPLETION in span.attributes

    def test_llm_call_content_not_captured_when_disabled(self, instrumentor):
        instrumentor.instrument()

        llm = _MockLLM(model="gpt-4o")
        llm.call([{"role": "user", "content": "secret"}])

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert ATTR_LLM_PROMPT not in span.attributes
        assert ATTR_LLM_COMPLETION not in span.attributes


# ---------------------------------------------------------------------------
# Tests: Metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_task_count_incremented(self, instrumentor):
        instrumentor.instrument()

        crew = _MockCrew(name="metric_crew", agents=[], tasks=[])
        crew.kickoff()

        assert instrumentor.metrics.get_counter("agent.task.count") >= 1

    def test_error_count_incremented_on_failure(self):
        def _failing_kickoff(self, *a, **kw):
            raise RuntimeError("boom")

        _MockCrew.kickoff = _failing_kickoff

        inst = CrewAIInstrumentor(capture_content=False)
        inst.instrument()

        crew = _MockCrew(name="err_crew")
        with pytest.raises(RuntimeError):
            crew.kickoff()

        assert inst.metrics.get_counter("agent.error.count") >= 1
        inst.uninstrument()

    def test_llm_metrics_recorded(self, instrumentor):
        instrumentor.instrument()

        llm = _MockLLM(model="gpt-4o")
        llm.call([{"role": "user", "content": "Hello"}])

        assert instrumentor.metrics.get_counter("agent.llm.call.count", model="gpt-4o") == 1
        assert instrumentor.metrics.get_counter("agent.llm.tokens.input", model="gpt-4o") == 100
        assert instrumentor.metrics.get_counter("agent.llm.tokens.output", model="gpt-4o") == 50


# ---------------------------------------------------------------------------
# Tests: Delegation detection
# ---------------------------------------------------------------------------

class TestDelegation:
    def test_delegation_detection_via_result_string(self):
        """When agent.execute_task returns a string containing 'delegate' or
        'coworker', the instrumentor should detect this and add a delegation
        event to the span."""
        def _delegate_result(self, *a, **kw):
            return "I will delegate this to my coworker for review"

        _MockAgent.execute_task = _delegate_result

        inst = CrewAIInstrumentor(capture_content=True)
        inst.instrument()

        agent = _MockAgent(role="manager")
        task = _MockTask(description="Delegate", agent=agent)
        agent.execute_task(task)

        spans = inst.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1
        events = reasoning_spans[0].events
        delegation_events = [e for e in events if "delegation" in e.name.lower()]
        assert len(delegation_events) >= 1

        inst.uninstrument()
