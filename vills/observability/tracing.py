"""Tracing OpenTelemetry — desativado de forma segura sem collector."""

from fastapi import FastAPI

from vills.core.settings import get_settings
from vills.observability.logging import get_logger

log = get_logger(__name__)


def configure_tracing(app: FastAPI) -> None:
    settings = get_settings()
    if not settings.otel_exporter_otlp_endpoint:
        log.info("tracing_disabled", reason="sem OTEL_EXPORTER_OTLP_ENDPOINT")
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    log.info("tracing_enabled", endpoint=settings.otel_exporter_otlp_endpoint)
