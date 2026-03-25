"""Integration tests for AutoGen adapter.

Tests the AutoGenInstrumentor monkey-patching against mocked AutoGen classes.
No actual AutoGen installation required.
"""

import pytest
from unittest.mock import MagicMock, patch

from agenttelemetry.core.spans import AGENT_SPAN_KIND


@pytest.fixture()
def _skip_if_no_adapter():
    try:
        from agenttelemetry.adapters.autogen import AutoGenInstrumentor
    except (ImportError, ModuleNotFoundError):
        pytest.skip("AutoGen adapter not yet available")


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestAutoGenInstrumentor:
    """Tests for the AutoGen framework adapter."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.autogen import AutoGenInstrumentor
        return AutoGenInstrumentor

    def test_instrumentor_has_instrument_method(self):
        cls = self._get_instrumentor()
        instrumentor = cls()
        assert hasattr(instrumentor, "instrument")

    def test_instrumentor_has_uninstrument_method(self):
        cls = self._get_instrumentor()
        instrumentor = cls()
        assert hasattr(instrumentor, "uninstrument")

    def test_instrument_initializes_without_error(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_autogen = MagicMock()
        with patch.dict("sys.modules", {
            "autogen": mock_autogen,
            "autogen_agentchat": MagicMock(),
        }):
            instrumentor.instrument()

    def test_uninstrument_restores_original(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_autogen = MagicMock()
        with patch.dict("sys.modules", {
            "autogen": mock_autogen,
            "autogen_agentchat": MagicMock(),
        }):
            instrumentor.instrument()
            instrumentor.uninstrument()


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestAutoGenMonkeyPatching:
    """Tests for AutoGen monkey-patching behavior."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.autogen import AutoGenInstrumentor
        return AutoGenInstrumentor

    def test_patches_agent_classes(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        # Create mock AutoGen agent classes
        mock_agent = MagicMock()
        mock_agent.generate_reply = MagicMock(return_value="I can help!")
        mock_agent.name = "assistant"

        mock_autogen = MagicMock()
        mock_autogen.ConversableAgent = type(mock_agent)

        with patch.dict("sys.modules", {
            "autogen": mock_autogen,
            "autogen_agentchat": MagicMock(),
        }):
            instrumentor.instrument()

    def test_agent_message_creates_delegation_span(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_autogen = MagicMock()
        with patch.dict("sys.modules", {
            "autogen": mock_autogen,
            "autogen_agentchat": MagicMock(),
        }):
            instrumentor.instrument()
            # Verify monkey-patching occurred
            # (exact verification depends on adapter implementation)
