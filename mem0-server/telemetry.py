"""
OpenTelemetry instrumentation for Engram memory server.

Provides distributed tracing to identify bottlenecks in:
- LLM extraction (slowest operation, typically 5-15s)
- Embedding generation (1-3s)
- Vector storage operations (~100-500ms)
- Neo4j graph sync (variable)
"""

import os
import time
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)

# Configuration
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "engram-memory")
OTEL_EXPORTER_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")

# Global tracer
_tracer: Optional[trace.Tracer] = None


def init_telemetry(app=None) -> trace.Tracer:
    """
    Initialize OpenTelemetry with OTLP exporter (Jaeger-compatible).

    Args:
        app: FastAPI application to instrument (optional)

    Returns:
        Configured tracer instance
    """
    global _tracer

    if not OTEL_ENABLED:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false)")
        _tracer = trace.get_tracer(__name__)
        return _tracer

    logger.info(f"Initializing OpenTelemetry: service={OTEL_SERVICE_NAME}, endpoint={OTEL_EXPORTER_ENDPOINT}")

    # Create resource with service info
    resource = Resource.create({
        "service.name": OTEL_SERVICE_NAME,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    # Set up tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter for Jaeger
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=OTEL_EXPORTER_ENDPOINT,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP exporter configured: {OTEL_EXPORTER_ENDPOINT}")
    except Exception as e:
        logger.warning(f"Failed to configure OTLP exporter: {e}. Traces will be local only.")

    # Set as global provider
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented")

    # Instrument HTTPX (for Ollama API calls)
    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX instrumented")

    _tracer = trace.get_tracer(__name__)
    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the configured tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


@contextmanager
def trace_operation(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True
):
    """
    Context manager for tracing operations with timing.

    Usage:
        with trace_operation("llm_extraction", {"model": "qwen3"}) as span:
            result = extract_facts(text)
            span.set_attribute("facts_count", len(result))
    """
    tracer = get_tracer()
    start_time = time.perf_counter()

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, str(value) if not isinstance(value, (int, float, bool)) else value)

        try:
            yield span
            duration_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("duration_ms", duration_ms)
            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("duration_ms", duration_ms)
            if record_exception:
                span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def traced(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    Decorator for tracing functions.

    Usage:
        @traced("memory.add")
        def add_memory(messages, user_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            with trace_operation(span_name, attributes) as span:
                # Add function arguments as attributes
                span.set_attribute("function.name", func.__name__)
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_operation(span_name, attributes) as span:
                span.set_attribute("function.name", func.__name__)
                return await func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# Pre-defined span names for consistency
class SpanNames:
    """Standard span names for Engram operations."""

    # Memory operations
    MEMORY_ADD = "memory.add"
    MEMORY_SEARCH = "memory.search"
    MEMORY_GET = "memory.get"
    MEMORY_DELETE = "memory.delete"

    # LLM operations (slowest)
    LLM_EXTRACTION = "llm.extraction"
    LLM_INFERENCE = "llm.inference"

    # Embedding operations
    EMBEDDING_GENERATE = "embedding.generate"
    EMBEDDING_SEARCH = "embedding.search"

    # Storage operations
    VECTOR_INSERT = "vector.insert"
    VECTOR_SEARCH = "vector.search"
    VECTOR_UPDATE = "vector.update"

    # Graph operations
    GRAPH_SYNC = "graph.sync"
    GRAPH_QUERY = "graph.query"
    GRAPH_ENRICH = "graph.enrich"


def add_memory_attributes(span, user_id: str = None, agent_id: str = None, message_count: int = None):
    """Add common memory operation attributes to a span."""
    if user_id:
        span.set_attribute("memory.user_id", user_id)
    if agent_id:
        span.set_attribute("memory.agent_id", agent_id)
    if message_count:
        span.set_attribute("memory.message_count", message_count)
