"""Convenience tracer setup for AgentTelemetry.

Provides a one-line configuration function and a provider class
that sets up OTel TracerProvider with agent-specific defaults.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.resources import Resource

from agenttelemetry.core.privacy import PrivacyLevel
from agenttelemetry.core.exporters import (
    AgentTelemetryConsoleExporter,
    AgentTelemetryJSONExporter,
)


class AgentTelemetryProvider:
    """Convenience class that wraps OTel TracerProvider with agent-specific defaults.

    Usage::

        provider = AgentTelemetryProvider(
            service_name="my-agent",
            privacy_level=PrivacyLevel.METADATA_ONLY,
        )
        provider.add_console_exporter()
        provider.add_json_exporter("traces.jsonl")
        provider.setup()

        tracer = provider.get_tracer("my-module")
    """

    def __init__(
        self,
        service_name: str = "agenttelemetry",
        privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
        resource_attributes: Optional[dict] = None,
    ) -> None:
        attrs = {"service.name": service_name}
        if resource_attributes:
            attrs.update(resource_attributes)
        self._resource = Resource.create(attrs)
        self._privacy_level = privacy_level
        self._exporters: List[SpanExporter] = []
        self._provider: Optional[TracerProvider] = None

    @property
    def privacy_level(self) -> PrivacyLevel:
        return self._privacy_level

    @property
    def tracer_provider(self) -> Optional[TracerProvider]:
        return self._provider

    def add_exporter(self, exporter: SpanExporter, batch: bool = True) -> None:
        """Add a custom exporter."""
        self._exporters.append((exporter, batch))

    def add_console_exporter(self, verbose: bool = False) -> None:
        """Add a console exporter (uses SimpleSpanProcessor for immediate output)."""
        self._exporters.append((AgentTelemetryConsoleExporter(verbose=verbose), False))

    def add_json_exporter(self, file_path: str = "agent_traces.jsonl") -> AgentTelemetryJSONExporter:
        """Add a JSON file exporter and return it for later access."""
        exporter = AgentTelemetryJSONExporter(file_path=file_path)
        self._exporters.append((exporter, False))
        return exporter

    def setup(self, set_global: bool = True) -> TracerProvider:
        """Create and configure the TracerProvider.

        Args:
            set_global: If True, sets this as the global tracer provider.

        Returns:
            The configured TracerProvider.
        """
        self._provider = TracerProvider(resource=self._resource)

        for exporter, batch in self._exporters:
            if batch:
                self._provider.add_span_processor(BatchSpanProcessor(exporter))
            else:
                self._provider.add_span_processor(SimpleSpanProcessor(exporter))

        if set_global:
            trace.set_tracer_provider(self._provider)

        return self._provider

    def get_tracer(self, name: str = "agenttelemetry") -> trace.Tracer:
        """Get an OTel Tracer from this provider."""
        if self._provider is None:
            self.setup()
        return self._provider.get_tracer(name, "0.1.0")

    def shutdown(self) -> None:
        """Shutdown the tracer provider and flush all exporters."""
        if self._provider:
            self._provider.shutdown()


def configure(
    service_name: str = "agenttelemetry",
    privacy_level: PrivacyLevel = PrivacyLevel.METADATA_ONLY,
    exporters: Optional[List[SpanExporter]] = None,
    console: bool = False,
    json_file: Optional[str] = None,
) -> AgentTelemetryProvider:
    """One-line setup for AgentTelemetry.

    Args:
        service_name: OTel service name.
        privacy_level: Privacy level for attribute filtering.
        exporters: Custom exporters to add.
        console: If True, add a console exporter.
        json_file: If provided, add a JSON file exporter at this path.

    Returns:
        Configured AgentTelemetryProvider.

    Usage::

        provider = configure(
            service_name="my-agent",
            console=True,
            json_file="traces.jsonl",
        )
        tracer = provider.get_tracer()
    """
    provider = AgentTelemetryProvider(
        service_name=service_name,
        privacy_level=privacy_level,
    )

    if console:
        provider.add_console_exporter()

    if json_file:
        provider.add_json_exporter(json_file)

    if exporters:
        for exp in exporters:
            provider.add_exporter(exp)

    provider.setup()
    return provider
