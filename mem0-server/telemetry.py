"""
Telemetry for Engram memory server.

Uses DuckDB for local trace storage - no external dependencies required.
Query traces via CLI: engram traces [command]
"""

import os
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

from trace_store import trace_span, Span, TRACES_ENABLED

logger = logging.getLogger(__name__)


def init_telemetry(app=None):
    """
    Initialize telemetry.

    Args:
        app: FastAPI application (for future instrumentation)

    Returns:
        None (telemetry is always available via trace_span)
    """
    if TRACES_ENABLED:
        logger.info("DuckDB trace storage enabled")
    else:
        logger.info("Trace storage disabled (TRACES_ENABLED=false)")


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
    with trace_span(name, attributes, record_exception) as span:
        yield span


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
                span.set_attribute("function.name", func.__name__)
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_operation(span_name, attributes) as span:
                span.set_attribute("function.name", func.__name__)
                return await func(*args, **kwargs)

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


def add_memory_attributes(span, user_id: str = None, agent_id: str = None, message_count: int = None):
    """Add common memory operation attributes to a span."""
    if user_id:
        span.set_attribute("user_id", user_id)
    if agent_id:
        span.set_attribute("agent_id", agent_id)
    if message_count:
        span.set_attribute("message_count", message_count)
