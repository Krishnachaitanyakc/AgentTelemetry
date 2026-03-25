"""Shared test fixtures for AgentTelemetry."""

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.resources import Resource


@pytest.fixture()
def memory_exporter():
    """An InMemorySpanExporter that captures spans for assertions."""
    return InMemorySpanExporter()


@pytest.fixture()
def fresh_tracer_provider(memory_exporter):
    """A fresh TracerProvider wired to InMemorySpanExporter.

    Does NOT set itself as the global provider to avoid cross-test interference.
    """
    resource = Resource.create({"service.name": "test-service"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(memory_exporter))
    yield provider
    provider.shutdown()


@pytest.fixture()
def tracer(fresh_tracer_provider):
    """A tracer obtained from the fresh provider."""
    return fresh_tracer_provider.get_tracer("test-tracer", "0.1.0")
