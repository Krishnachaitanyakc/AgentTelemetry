"""Integration tests for the DSPy instrumentor.

Uses mock objects to simulate DSPy's Predict, Module, Retrieve,
ChainOfThought, and ReAct classes so tests can run without installing
dspy-ai.  Exercises instrument/uninstrument, span creation, attribute
setting, metric recording, content capture, and error handling.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock dspy package before importing the instrumentor
# ---------------------------------------------------------------------------

_dspy = types.ModuleType("dspy")
_dspy.__version__ = "2.5.0"


class _MockSettings:
    """Stand-in for dspy.settings."""
    lm = None


class _MockLM:
    """Minimal LM object with model name and history."""
    def __init__(self, model="gpt-4o"):
        self.model = model
        self.history = []


class _MockPrediction:
    """Minimal prediction result."""
    def __init__(self, answer="42", rationale=None):
        self.answer = answer
        self.rationale = rationale

    def __str__(self):
        return f"Prediction(answer={self.answer})"


class _MockSignature:
    """Minimal DSPy signature."""
    def __init__(self, sig_str="question -> answer"):
        self._str = sig_str
        self.input_fields = {"question": "input field"}
        self.output_fields = {"answer": "output field"}
        self.instructions = "Answer the question."

    def __str__(self):
        return self._str


class _MockPredict:
    """Minimal stand-in for dspy.Predict."""
    def __init__(self, signature=None):
        self.signature = signature or _MockSignature()
        self.name = "predict"
        self.demos = []

    def __call__(self, *args, **kwargs):
        return _MockPrediction(answer="test answer")


class _MockModule:
    """Minimal stand-in for dspy.Module."""
    def __init__(self):
        self.name = "TestModule"

    def __call__(self, *args, **kwargs):
        return _MockPrediction(answer="module output")

    def forward(self, *args, **kwargs):
        return _MockPrediction(answer="module output")


class _MockRetrieve:
    """Minimal stand-in for dspy.Retrieve."""
    def __init__(self, k=3):
        self.k = k

    def __call__(self, query=None, *args, **kwargs):
        result = MagicMock()
        result.passages = ["doc1", "doc2", "doc3"]
        return result


class _MockChainOfThought:
    """Minimal stand-in for dspy.ChainOfThought."""
    def __init__(self, signature=None):
        self.signature = signature or _MockSignature("question -> rationale, answer")
        self.name = "cot_predictor"
        self.demos = []

    def __call__(self, *args, **kwargs):
        return _MockPrediction(answer="reasoned answer", rationale="because I thought about it")


class _MockReAct:
    """Minimal stand-in for dspy.ReAct."""
    def __init__(self, signature=None, tools=None, max_iters=5):
        self.signature = signature or _MockSignature("question -> answer")
        self.name = "react_agent"
        self.tools = tools or []
        self.max_iters = max_iters

    def __call__(self, *args, **kwargs):
        result = _MockPrediction(answer="final answer")
        result.thought_1 = "I need to search for info"
        result.action_1 = "search"
        result.observation_1 = "Found relevant data"
        result.thought_2 = "Now I can answer"
        result.action_2 = None
        result.observation_2 = None
        return result


_dspy.settings = _MockSettings()
_dspy.Predict = _MockPredict
_dspy.Module = _MockModule
_dspy.Retrieve = _MockRetrieve
_dspy.ChainOfThought = _MockChainOfThought
_dspy.ReAct = _MockReAct

sys.modules.setdefault("dspy", _dspy)

from agenttelemetry.core.trace import (  # noqa: E402
    ATTR_LLM_COMPLETION,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    AgentSpanKind,
    SpanStatus,
)
from agenttelemetry.instrumentors.dspy import (  # noqa: E402
    ATTR_DSPY_DEMOS_COUNT,
    ATTR_DSPY_MODULE_TYPE,
    ATTR_DSPY_PREDICTOR_NAME,
    ATTR_DSPY_REACT_PHASE,
    ATTR_DSPY_REACT_STEP,
    ATTR_DSPY_RETRIEVAL_K,
    ATTR_DSPY_RETRIEVAL_RESULTS_COUNT,
    ATTR_DSPY_SIGNATURE,
    ATTR_DSPY_SIGNATURE_INPUT_FIELDS,
    ATTR_DSPY_SIGNATURE_OUTPUT_FIELDS,
    DSPyInstrumentor,
)


# ---------------------------------------------------------------------------
# Save originals for restoration
# ---------------------------------------------------------------------------

_SAVED_PREDICT_CALL = _MockPredict.__call__
_SAVED_MODULE_CALL = _MockModule.__call__
_SAVED_RETRIEVE_CALL = _MockRetrieve.__call__
_SAVED_COT_CALL = _MockChainOfThought.__call__
_SAVED_REACT_CALL = _MockReAct.__call__


@pytest.fixture(autouse=True)
def restore_mock_methods():
    """Ensure mock class methods are restored after each test."""
    yield
    _MockPredict.__call__ = _SAVED_PREDICT_CALL
    _MockModule.__call__ = _SAVED_MODULE_CALL
    _MockRetrieve.__call__ = _SAVED_RETRIEVE_CALL
    _MockChainOfThought.__call__ = _SAVED_COT_CALL
    _MockReAct.__call__ = _SAVED_REACT_CALL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def instrumentor():
    inst = DSPyInstrumentor(capture_content=False)
    yield inst
    if inst.is_instrumented:
        inst.uninstrument()


@pytest.fixture()
def instrumentor_with_content():
    inst = DSPyInstrumentor(capture_content=True)
    yield inst
    if inst.is_instrumented:
        inst.uninstrument()


@pytest.fixture(autouse=True)
def setup_lm():
    """Ensure a mock LM is set on dspy.settings before each test."""
    _dspy.settings.lm = _MockLM(model="gpt-4o")
    _dspy.settings.lm.history = [
        {
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
    ]
    yield
    _dspy.settings.lm = None


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
        instrumentor.instrument()
        assert instrumentor.is_instrumented is True

    def test_double_uninstrument_is_noop(self, instrumentor):
        instrumentor.instrument()
        instrumentor.uninstrument()
        instrumentor.uninstrument()
        assert instrumentor.is_instrumented is False

    def test_framework_name(self, instrumentor):
        assert instrumentor.framework_name == "dspy"

    def test_uninstrument_restores_originals(self, instrumentor):
        orig_predict = _MockPredict.__call__
        orig_module = _MockModule.__call__
        orig_retrieve = _MockRetrieve.__call__
        orig_cot = _MockChainOfThought.__call__
        orig_react = _MockReAct.__call__

        instrumentor.instrument()
        assert _MockPredict.__call__ is not orig_predict
        assert _MockModule.__call__ is not orig_module
        assert _MockRetrieve.__call__ is not orig_retrieve
        assert _MockChainOfThought.__call__ is not orig_cot
        assert _MockReAct.__call__ is not orig_react

        instrumentor.uninstrument()
        assert _MockPredict.__call__ is orig_predict
        assert _MockModule.__call__ is orig_module
        assert _MockRetrieve.__call__ is orig_retrieve
        assert _MockChainOfThought.__call__ is orig_cot
        assert _MockReAct.__call__ is orig_react


# ---------------------------------------------------------------------------
# Tests: Predict.__call__  (LLM_CALL spans)
# ---------------------------------------------------------------------------

class TestPredictCall:
    def test_predict_creates_llm_call_span(self, instrumentor):
        instrumentor.instrument()

        predictor = _MockPredict()
        result = predictor(question="What is 2+2?")

        assert result.answer == "test answer"

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        assert len(llm_spans) == 1

    def test_predict_span_attributes(self, instrumentor):
        instrumentor.instrument()

        predictor = _MockPredict()
        predictor(question="test")

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert span.attributes[ATTR_LLM_MODEL] == "gpt-4o"
        assert span.attributes[ATTR_DSPY_MODULE_TYPE] == "Predict"
        assert span.attributes[ATTR_DSPY_PREDICTOR_NAME] == "predict"
        assert span.attributes[ATTR_DSPY_DEMOS_COUNT] == 0
        assert ATTR_DSPY_SIGNATURE in span.attributes
        assert ATTR_DSPY_SIGNATURE_INPUT_FIELDS in span.attributes
        assert ATTR_DSPY_SIGNATURE_OUTPUT_FIELDS in span.attributes

    def test_predict_token_usage(self, instrumentor):
        instrumentor.instrument()

        predictor = _MockPredict()
        predictor(question="test")

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert span.attributes[ATTR_LLM_INPUT_TOKENS] == 100
        assert span.attributes[ATTR_LLM_OUTPUT_TOKENS] == 50

    def test_predict_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        predictor = _MockPredict()
        predictor(question="What is AI?")

        spans = inst.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert ATTR_LLM_PROMPT in span.attributes
        assert ATTR_LLM_COMPLETION in span.attributes

    def test_predict_content_not_captured(self, instrumentor):
        instrumentor.instrument()

        predictor = _MockPredict()
        predictor(question="secret question")

        spans = instrumentor.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        span = llm_spans[0]
        assert ATTR_LLM_PROMPT not in span.attributes
        assert ATTR_LLM_COMPLETION not in span.attributes

    def test_predict_error(self):
        def _failing_predict(self, *a, **kw):
            raise ValueError("prediction failed")

        _MockPredict.__call__ = _failing_predict

        inst = DSPyInstrumentor(capture_content=False)
        inst.instrument()

        predictor = _MockPredict()
        with pytest.raises(ValueError, match="prediction failed"):
            predictor(question="fail")

        spans = inst.tracer.get_spans()
        llm_spans = [s for s in spans if s.kind == AgentSpanKind.LLM_CALL]
        assert len(llm_spans) == 1
        assert llm_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()

    def test_predict_metrics(self, instrumentor):
        instrumentor.instrument()

        predictor = _MockPredict()
        predictor(question="test")

        assert instrumentor.metrics.get_counter("agent.llm.call.count", model="gpt-4o") == 1
        assert instrumentor.metrics.get_counter("agent.llm.tokens.input", model="gpt-4o") == 100
        assert instrumentor.metrics.get_counter("agent.llm.tokens.output", model="gpt-4o") == 50


# ---------------------------------------------------------------------------
# Tests: Module.__call__  (TASK spans)
# ---------------------------------------------------------------------------

class TestModuleCall:
    def test_module_creates_task_span(self, instrumentor):
        instrumentor.instrument()

        module = _MockModule()
        result = module(question="test")

        spans = instrumentor.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        assert len(task_spans) == 1
        span = task_spans[0]
        assert span.attributes[ATTR_DSPY_MODULE_TYPE] == "_MockModule"

    def test_module_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        module = _MockModule()
        module(question="What is ML?")

        spans = inst.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        span = task_spans[0]
        assert "dspy.module.input" in span.attributes
        assert "dspy.module.output" in span.attributes

    def test_module_error(self):
        def _failing_module(self, *a, **kw):
            raise RuntimeError("module crashed")

        _MockModule.__call__ = _failing_module

        inst = DSPyInstrumentor(capture_content=False)
        inst.instrument()

        module = _MockModule()
        with pytest.raises(RuntimeError, match="module crashed"):
            module(question="fail")

        spans = inst.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        assert len(task_spans) == 1
        assert task_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()

    def test_module_metrics(self, instrumentor):
        instrumentor.instrument()

        module = _MockModule()
        module(question="test")

        assert instrumentor.metrics.get_counter("agent.task.count", framework="dspy") >= 1


# ---------------------------------------------------------------------------
# Tests: Retrieve.__call__  (RETRIEVAL spans)
# ---------------------------------------------------------------------------

class TestRetrieveCall:
    def test_retrieve_creates_retrieval_span(self, instrumentor):
        instrumentor.instrument()

        retriever = _MockRetrieve(k=3)
        result = retriever(query="search query")

        spans = instrumentor.tracer.get_spans()
        retrieval_spans = [s for s in spans if s.kind == AgentSpanKind.RETRIEVAL]
        assert len(retrieval_spans) == 1
        span = retrieval_spans[0]
        assert span.attributes[ATTR_DSPY_MODULE_TYPE] == "Retrieve"
        assert span.attributes[ATTR_TOOL_NAME] == "dspy.Retrieve"
        assert span.attributes[ATTR_DSPY_RETRIEVAL_K] == 3
        assert span.attributes[ATTR_TOOL_SUCCESS] is True

    def test_retrieve_results_count(self, instrumentor):
        instrumentor.instrument()

        retriever = _MockRetrieve(k=3)
        retriever(query="test")

        spans = instrumentor.tracer.get_spans()
        retrieval_spans = [s for s in spans if s.kind == AgentSpanKind.RETRIEVAL]
        span = retrieval_spans[0]
        assert span.attributes[ATTR_DSPY_RETRIEVAL_RESULTS_COUNT] == 3

    def test_retrieve_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        retriever = _MockRetrieve(k=3)
        retriever(query="important query")

        spans = inst.tracer.get_spans()
        retrieval_spans = [s for s in spans if s.kind == AgentSpanKind.RETRIEVAL]
        span = retrieval_spans[0]
        assert "dspy.retrieval.query" in span.attributes
        assert ATTR_TOOL_OUTPUT in span.attributes

    def test_retrieve_content_not_captured(self, instrumentor):
        instrumentor.instrument()

        retriever = _MockRetrieve(k=3)
        retriever(query="secret query")

        spans = instrumentor.tracer.get_spans()
        retrieval_spans = [s for s in spans if s.kind == AgentSpanKind.RETRIEVAL]
        span = retrieval_spans[0]
        assert "dspy.retrieval.query" not in span.attributes

    def test_retrieve_error(self):
        def _failing_retrieve(self, *a, **kw):
            raise ConnectionError("retrieval failed")

        _MockRetrieve.__call__ = _failing_retrieve

        inst = DSPyInstrumentor(capture_content=False)
        inst.instrument()

        retriever = _MockRetrieve()
        with pytest.raises(ConnectionError, match="retrieval failed"):
            retriever(query="fail")

        spans = inst.tracer.get_spans()
        retrieval_spans = [s for s in spans if s.kind == AgentSpanKind.RETRIEVAL]
        assert len(retrieval_spans) == 1
        assert retrieval_spans[0].status == SpanStatus.ERROR
        assert retrieval_spans[0].attributes[ATTR_TOOL_SUCCESS] is False

        inst.uninstrument()

    def test_retrieve_metrics(self, instrumentor):
        instrumentor.instrument()

        retriever = _MockRetrieve(k=3)
        retriever(query="test")

        assert instrumentor.metrics.get_counter("agent.tool.call.count", tool="dspy.Retrieve") == 1


# ---------------------------------------------------------------------------
# Tests: ChainOfThought.__call__  (REASONING spans)
# ---------------------------------------------------------------------------

class TestChainOfThoughtCall:
    def test_cot_creates_reasoning_span(self, instrumentor):
        instrumentor.instrument()

        cot = _MockChainOfThought()
        result = cot(question="Why is the sky blue?")

        assert result.answer == "reasoned answer"

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1
        span = reasoning_spans[0]
        assert span.attributes[ATTR_DSPY_MODULE_TYPE] == "ChainOfThought"

    def test_cot_span_attributes(self, instrumentor):
        instrumentor.instrument()

        cot = _MockChainOfThought()
        cot(question="test")

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert span.attributes[ATTR_DSPY_PREDICTOR_NAME] == "cot_predictor"
        assert ATTR_DSPY_SIGNATURE in span.attributes

    def test_cot_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        cot = _MockChainOfThought()
        cot(question="Explain entropy")

        spans = inst.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert "dspy.cot.input" in span.attributes
        assert "dspy.cot.output" in span.attributes
        assert "dspy.cot.rationale" in span.attributes

    def test_cot_content_not_captured(self, instrumentor):
        instrumentor.instrument()

        cot = _MockChainOfThought()
        cot(question="secret")

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        span = reasoning_spans[0]
        assert "dspy.cot.input" not in span.attributes
        assert "dspy.cot.output" not in span.attributes

    def test_cot_error(self):
        def _failing_cot(self, *a, **kw):
            raise RuntimeError("reasoning failed")

        _MockChainOfThought.__call__ = _failing_cot

        inst = DSPyInstrumentor(capture_content=False)
        inst.instrument()

        cot = _MockChainOfThought()
        with pytest.raises(RuntimeError, match="reasoning failed"):
            cot(question="fail")

        spans = inst.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        assert len(reasoning_spans) >= 1
        assert reasoning_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()


# ---------------------------------------------------------------------------
# Tests: ReAct.__call__  (TASK + REASONING spans)
# ---------------------------------------------------------------------------

class TestReActCall:
    def test_react_creates_task_span(self, instrumentor):
        instrumentor.instrument()

        tool = MagicMock()
        tool.name = "search"
        react = _MockReAct(tools=[tool], max_iters=5)
        result = react(question="Find info about Python")

        assert result.answer == "final answer"

        spans = instrumentor.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        assert len(task_spans) >= 1
        span = task_spans[0]
        assert span.attributes[ATTR_DSPY_MODULE_TYPE] == "ReAct"

    def test_react_step_reasoning_spans(self, instrumentor):
        instrumentor.instrument()

        react = _MockReAct()
        react(question="test")

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        step_spans = [s for s in reasoning_spans if ATTR_DSPY_REACT_STEP in s.attributes]
        assert len(step_spans) >= 1

    def test_react_step_attributes(self, instrumentor):
        instrumentor.instrument()

        react = _MockReAct()
        react(question="test")

        spans = instrumentor.tracer.get_spans()
        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        step_spans = [s for s in reasoning_spans if ATTR_DSPY_REACT_STEP in s.attributes]

        step1 = [s for s in step_spans if s.attributes.get(ATTR_DSPY_REACT_STEP) == 1]
        assert len(step1) == 1

    def test_react_content_captured(self, instrumentor_with_content):
        inst = instrumentor_with_content
        inst.instrument()

        react = _MockReAct()
        react(question="Explain gravity")

        spans = inst.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        span = task_spans[0]
        assert "dspy.react.input" in span.attributes
        assert "dspy.react.output" in span.attributes

        reasoning_spans = [s for s in spans if s.kind == AgentSpanKind.REASONING]
        step_spans = [s for s in reasoning_spans if ATTR_DSPY_REACT_STEP in s.attributes]
        if step_spans:
            assert "dspy.react.thought" in step_spans[0].attributes

    def test_react_content_not_captured(self, instrumentor):
        instrumentor.instrument()

        react = _MockReAct()
        react(question="secret")

        spans = instrumentor.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        span = task_spans[0]
        assert "dspy.react.input" not in span.attributes

    def test_react_error(self):
        def _failing_react(self, *a, **kw):
            raise RuntimeError("react loop failed")

        _MockReAct.__call__ = _failing_react

        inst = DSPyInstrumentor(capture_content=False)
        inst.instrument()

        react = _MockReAct()
        with pytest.raises(RuntimeError, match="react loop failed"):
            react(question="fail")

        spans = inst.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        assert len(task_spans) >= 1
        assert task_spans[0].status == SpanStatus.ERROR

        inst.uninstrument()

    def test_react_total_steps(self, instrumentor):
        instrumentor.instrument()

        react = _MockReAct()
        react(question="test")

        spans = instrumentor.tracer.get_spans()
        task_spans = [s for s in spans if s.kind == AgentSpanKind.TASK]
        span = task_spans[0]
        assert span.attributes.get("dspy.react.total_steps") == 2

    def test_react_metrics(self, instrumentor):
        instrumentor.instrument()

        react = _MockReAct()
        react(question="test")

        assert instrumentor.metrics.get_counter("agent.task.count", framework="dspy") >= 1
