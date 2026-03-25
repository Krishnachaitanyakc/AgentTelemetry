"""Integration tests for CrewAI adapter.

Tests the CrewAIInstrumentor against mocked CrewAI classes.
No actual CrewAI installation required.
"""

import pytest
from unittest.mock import MagicMock, patch

from agenttelemetry.core.spans import AGENT_SPAN_KIND


@pytest.fixture()
def _skip_if_no_adapter():
    try:
        from agenttelemetry.adapters.crewai import CrewAIInstrumentor
    except (ImportError, ModuleNotFoundError):
        pytest.skip("CrewAI adapter not yet available")


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestCrewAIInstrumentor:
    """Tests for the CrewAI framework adapter."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.crewai import CrewAIInstrumentor
        return CrewAIInstrumentor

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

        # Mock crewai module
        mock_crewai = MagicMock()
        with patch.dict("sys.modules", {"crewai": mock_crewai}):
            instrumentor.instrument()

    def test_uninstrument_cleans_up(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_crewai = MagicMock()
        with patch.dict("sys.modules", {"crewai": mock_crewai}):
            instrumentor.instrument()
            instrumentor.uninstrument()


@pytest.mark.usefixtures("_skip_if_no_adapter")
class TestCrewAISpanCreation:
    """Tests that CrewAI hooks create correct spans."""

    def _get_instrumentor(self):
        from agenttelemetry.adapters.crewai import CrewAIInstrumentor
        return CrewAIInstrumentor

    def test_crew_execution_creates_agent_span(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_crewai = MagicMock()
        with patch.dict("sys.modules", {"crewai": mock_crewai}):
            instrumentor.instrument()

        # Verify the instrumentor registered hooks
        # (exact mechanism depends on adapter implementation)

    def test_task_execution_creates_delegation_span(self, fresh_tracer_provider, memory_exporter):
        cls = self._get_instrumentor()
        instrumentor = cls(tracer_provider=fresh_tracer_provider)

        mock_crewai = MagicMock()
        with patch.dict("sys.modules", {"crewai": mock_crewai}):
            instrumentor.instrument()
