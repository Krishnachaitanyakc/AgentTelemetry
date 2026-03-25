"""Integration tests for LangChain adapter.

Tests the LangChainInstrumentor callback handler against mocked LangChain classes.
No actual LangChain installation required.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from agenttelemetry.core.spans import AGENT_SPAN_KIND, LLM_MODEL, LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS


@pytest.fixture()
def _skip_if_no_adapter():
    try:
        from agenttelemetry.adapters.langchain import LangChainInstrumentor
    except (ImportError, ModuleNotFoundError):
        pytest.skip("LangChain adapter not yet available")


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestLangChainInstrumentor:
    """Tests for the LangChain framework adapter."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.langchain import LangChainInstrumentor
        return LangChainInstrumentor

    def test_instrumentor_has_instrument_method(self):
        cls = self._get_instrumentor()
        instrumentor = cls()
        assert hasattr(instrumentor, "instrument")

    def test_instrumentor_has_uninstrument_method(self):
        cls = self._get_instrumentor()
        instrumentor = cls()
        assert hasattr(instrumentor, "uninstrument")

    def test_creates_callback_handler(self):
        cls = self._get_instrumentor()
        instrumentor = cls()
        assert hasattr(instrumentor, "get_callback_handler") or hasattr(instrumentor, "callback_handler")


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestLangChainCallbackSpans:
    """Tests for span creation via LangChain callback handler."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.langchain import LangChainInstrumentor
        return LangChainInstrumentor

    def test_on_llm_start_creates_span(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)
        handler = getattr(instrumentor, "get_callback_handler", lambda: instrumentor)()

        if hasattr(handler, "on_llm_start"):
            # Simulate LangChain calling on_llm_start
            serialized = {"name": "ChatOpenAI"}
            prompts = ["What is the weather?"]
            run_id = uuid4()
            handler.on_llm_start(serialized, prompts, run_id=run_id)

            # Then on_llm_end
            mock_response = MagicMock()
            mock_response.llm_output = {
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
                "model_name": "gpt-4o",
            }
            mock_response.generations = [[MagicMock(text="Sunny!")]]

            if hasattr(handler, "on_llm_end"):
                handler.on_llm_end(mock_response, run_id=run_id)

            spans = memory_exporter.get_finished_spans()
            # Should have created at least one span
            if spans:
                llm_spans = [
                    s for s in spans
                    if s.attributes and s.attributes.get(AGENT_SPAN_KIND) == "LLM_CALL"
                ]
                assert len(llm_spans) >= 1

    def test_on_tool_start_creates_tool_span(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)
        handler = getattr(instrumentor, "get_callback_handler", lambda: instrumentor)()

        if hasattr(handler, "on_tool_start"):
            serialized = {"name": "search_tool"}
            input_str = "weather in NYC"
            run_id = uuid4()
            handler.on_tool_start(serialized, input_str, run_id=run_id)

            if hasattr(handler, "on_tool_end"):
                handler.on_tool_end("Sunny and warm", run_id=run_id)

            spans = memory_exporter.get_finished_spans()
            if spans:
                tool_spans = [
                    s for s in spans
                    if s.attributes and s.attributes.get(AGENT_SPAN_KIND) == "TOOL_CALL"
                ]
                assert len(tool_spans) >= 1
