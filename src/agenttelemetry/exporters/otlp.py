"""OpenTelemetry Protocol (OTLP) exporter.

Bridges AgentTelemetry spans to OpenTelemetry, enabling export to any
OTel-compatible backend (Jaeger, Grafana Tempo, Datadog, etc.).

Requires: pip install agenttelemetry[otlp]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agenttelemetry.core.trace import AgentSpan


class OTLPExporter:
    """Exports agent spans via OpenTelemetry Protocol.

    Converts AgentSpan instances to OTel Spans and exports them
    through the configured OTel exporter (gRPC or HTTP).
    """

    def __init__(self, endpoint: str = "http://localhost:4317", service_name: str = "agenttelemetry"):
        try:
            from opentelemetry import trace as otel_trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource
        except ImportError:
            raise ImportError(
                "OpenTelemetry packages required. Install with: "
                "pip install agenttelemetry[otlp]"
            )

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        otel_trace.set_tracer_provider(provider)
        self._tracer = otel_trace.get_tracer("agenttelemetry")
        self._otel_trace = otel_trace

    def export_span(self, span: "AgentSpan") -> None:
        """Convert and export an AgentSpan as an OTel span."""
        otel_span = self._tracer.start_span(
            name=span.name,
            attributes={
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in span.attributes.items()
            },
        )
        otel_span.set_attribute("agent.span.kind", span.kind.value)
        otel_span.set_attribute("agent.span.trace_id", span.trace_id)

        for event in span.events:
            otel_span.add_event(
                event.name,
                attributes={
                    k: str(v) for k, v in event.attributes.items()
                },
            )

        if span.status.value == "error":
            otel_span.set_status(self._otel_trace.StatusCode.ERROR)
        else:
            otel_span.set_status(self._otel_trace.StatusCode.OK)

        otel_span.end()
