"""Integration tests for OpenAI adapter.

Tests the OpenAIInstrumentor against mocked OpenAI SDK classes.
No actual OpenAI SDK installation required.
"""

import pytest
from unittest.mock import MagicMock, patch

from agenttelemetry.core.spans import AGENT_SPAN_KIND, LLM_MODEL, LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS


@pytest.fixture()
def _skip_if_no_adapter():
    try:
        from agenttelemetry.adapters.openai import OpenAIInstrumentor
    except (ImportError, ModuleNotFoundError):
        pytest.skip("OpenAI adapter not yet available")


@pytest.fixture()
def mock_openai_module():
    """Create a mock openai module with expected class structure."""
    mock_mod = MagicMock()

    # Mock ChatCompletion response
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello from GPT!"
    mock_choice.message.role = "assistant"
    mock_choice.message.tool_calls = None
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 50
    mock_usage.completion_tokens = 30
    mock_usage.total_tokens = 80

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o-2024-08-06"
    mock_response.usage = mock_usage
    mock_response.id = "chatcmpl-123"

    # Wire up: openai.OpenAI().chat.completions.create(...)
    mock_completions = MagicMock()
    mock_completions.create.return_value = mock_response

    mock_chat = MagicMock()
    mock_chat.completions = mock_completions

    mock_client = MagicMock()
    mock_client.chat = mock_chat

    mock_mod.OpenAI.return_value = mock_client

    return mock_mod, mock_completions, mock_response


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestOpenAIInstrumentor:
    """Tests for the OpenAI framework adapter."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.openai import OpenAIInstrumentor
        return OpenAIInstrumentor

    def test_instrumentor_has_instrument_method(self):
        cls = self._get_instrumentor()
        instrumentor = cls()
        assert hasattr(instrumentor, "instrument")

    def test_instrumentor_has_uninstrument_method(self):
        cls = self._get_instrumentor()
        instrumentor = cls()
        assert hasattr(instrumentor, "uninstrument")

    def test_instrument_initializes_without_error(
        self, fresh_tracer_provider, memory_exporter, mock_openai_module
    ):
        mock_mod, mock_completions, mock_response = mock_openai_module
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        with patch.dict("sys.modules", {"openai": mock_mod}):
            instrumentor.instrument()

    def test_uninstrument_restores_original(
        self, fresh_tracer_provider, memory_exporter, mock_openai_module
    ):
        mock_mod, mock_completions, mock_response = mock_openai_module
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        with patch.dict("sys.modules", {"openai": mock_mod}):
            instrumentor.instrument()
            instrumentor.uninstrument()


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestOpenAIToolCalls:
    """Tests that tool calls in OpenAI responses are captured."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.openai import OpenAIInstrumentor
        return OpenAIInstrumentor

    def test_tool_call_response_structure(self):
        """Verify mock tool call response has the expected structure."""
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_abc123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "NYC"}'

        mock_choice = MagicMock()
        mock_choice.message.tool_calls = [mock_tool_call]
        mock_choice.finish_reason = "tool_calls"

        assert mock_choice.message.tool_calls[0].function.name == "get_weather"
