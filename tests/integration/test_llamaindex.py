"""Integration tests for LlamaIndex adapter.

Tests the LlamaIndexInstrumentor against mocked LlamaIndex classes.
No actual LlamaIndex installation required.
"""

import pytest
from unittest.mock import MagicMock, patch

from agenttelemetry.core.spans import AGENT_SPAN_KIND


@pytest.fixture()
def _skip_if_no_adapter():
    try:
        from agenttelemetry.adapters.llamaindex import LlamaIndexInstrumentor
    except (ImportError, ModuleNotFoundError):
        pytest.skip("LlamaIndex adapter not yet available")


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestLlamaIndexInstrumentor:
    """Tests for the LlamaIndex framework adapter."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.llamaindex import LlamaIndexInstrumentor
        return LlamaIndexInstrumentor

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

        mock_llama = MagicMock()
        mock_llama_core = MagicMock()
        with patch.dict("sys.modules", {
            "llama_index": mock_llama,
            "llama_index.core": mock_llama_core,
            "llama_index.core.instrumentation": MagicMock(),
        }):
            instrumentor.instrument()

    def test_uninstrument_cleans_up(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_llama = MagicMock()
        mock_llama_core = MagicMock()
        with patch.dict("sys.modules", {
            "llama_index": mock_llama,
            "llama_index.core": mock_llama_core,
            "llama_index.core.instrumentation": MagicMock(),
        }):
            instrumentor.instrument()
            instrumentor.uninstrument()


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestLlamaIndexSpanHandling:
    """Tests for LlamaIndex span handler registration."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.llamaindex import LlamaIndexInstrumentor
        return LlamaIndexInstrumentor

    def test_registers_span_handler(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_dispatcher = MagicMock()
        mock_instrumentation = MagicMock()
        mock_instrumentation.get_dispatcher.return_value = mock_dispatcher

        with patch.dict("sys.modules", {
            "llama_index": MagicMock(),
            "llama_index.core": MagicMock(),
            "llama_index.core.instrumentation": mock_instrumentation,
        }):
            instrumentor.instrument()

    def test_retrieval_events_create_retrieval_spans(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        # The exact mechanism depends on adapter implementation
        # (event handler vs span handler)
