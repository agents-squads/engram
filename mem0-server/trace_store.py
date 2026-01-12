"""
DuckDB-based trace storage for Engram.

Provides local, queryable trace storage without external dependencies.
Traces are stored in a DuckDB file and can be queried via CLI or SQL.
"""

import os
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuration
TRACES_ENABLED = os.getenv("TRACES_ENABLED", "true").lower() == "true"
TRACES_DB_PATH = os.getenv("TRACES_DB_PATH", "/app/data/traces.duckdb")
TRACES_RETENTION_DAYS = int(os.getenv("TRACES_RETENTION_DAYS", "365"))

# Global connection (thread-local for safety)
_local = threading.local()


def _get_connection():
    """Get thread-local DuckDB connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        try:
            import duckdb
            # Ensure directory exists
            db_dir = os.path.dirname(TRACES_DB_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            _local.conn = duckdb.connect(TRACES_DB_PATH)
            _init_schema(_local.conn)
            logger.info(f"DuckDB trace store initialized: {TRACES_DB_PATH}")
        except ImportError:
            logger.warning("DuckDB not installed. Traces will not be stored.")
            _local.conn = None
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB: {e}")
            _local.conn = None
    return _local.conn


def _init_schema(conn):
    """Initialize the trace schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS spans (
            -- Identity
            span_id VARCHAR PRIMARY KEY,
            trace_id VARCHAR NOT NULL,
            parent_span_id VARCHAR,

            -- Timing
            name VARCHAR NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration_ms DOUBLE,

            -- Status
            status VARCHAR DEFAULT 'OK',  -- OK, ERROR
            error_message VARCHAR,

            -- Context
            service_name VARCHAR DEFAULT 'engram',
            user_id VARCHAR,
            agent_id VARCHAR,

            -- Attributes (JSON)
            attributes JSON,

            -- Indexes for common queries
        );

        CREATE INDEX IF NOT EXISTS idx_spans_trace_id ON spans(trace_id);
        CREATE INDEX IF NOT EXISTS idx_spans_start_time ON spans(start_time);
        CREATE INDEX IF NOT EXISTS idx_spans_name ON spans(name);
        CREATE INDEX IF NOT EXISTS idx_spans_user_id ON spans(user_id);
        CREATE INDEX IF NOT EXISTS idx_spans_status ON spans(status);
    """)


class Span:
    """A trace span that records timing and attributes."""

    def __init__(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.span_id = str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.name = name
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.duration_ms: Optional[float] = None
        self.status = "OK"
        self.error_message: Optional[str] = None
        self.attributes = attributes or {}
        self._start_perf = time.perf_counter()

    def set_attribute(self, key: str, value: Any):
        """Set an attribute on the span."""
        if value is not None:
            self.attributes[key] = value

    def set_status(self, status: str, message: Optional[str] = None):
        """Set span status (OK or ERROR)."""
        self.status = status
        if message:
            self.error_message = message

    def record_exception(self, exception: Exception):
        """Record an exception on the span."""
        self.status = "ERROR"
        self.error_message = str(exception)
        self.attributes["exception.type"] = type(exception).__name__
        self.attributes["exception.message"] = str(exception)

    def end(self):
        """End the span and calculate duration."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (time.perf_counter() - self._start_perf) * 1000
        self._save()

    def _save(self):
        """Save span to DuckDB."""
        if not TRACES_ENABLED:
            return

        conn = _get_connection()
        if conn is None:
            return

        try:
            import json
            conn.execute("""
                INSERT INTO spans (
                    span_id, trace_id, parent_span_id,
                    name, start_time, end_time, duration_ms,
                    status, error_message,
                    user_id, agent_id, attributes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                self.span_id,
                self.trace_id,
                self.parent_span_id,
                self.name,
                self.start_time,
                self.end_time,
                self.duration_ms,
                self.status,
                self.error_message,
                self.attributes.get("user_id"),
                self.attributes.get("agent_id"),
                json.dumps(self.attributes) if self.attributes else None
            ])
        except Exception as e:
            logger.error(f"Failed to save span: {e}")


# Thread-local current span for nesting
_current_span: Optional[Span] = None


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True
):
    """
    Context manager for creating trace spans.

    Usage:
        with trace_span("memory.add", {"user_id": "abc"}) as span:
            result = do_work()
            span.set_attribute("result_count", len(result))
    """
    global _current_span

    parent_id = _current_span.span_id if _current_span else None
    trace_id = _current_span.trace_id if _current_span else None

    span = Span(
        name=name,
        trace_id=trace_id,
        parent_span_id=parent_id,
        attributes=attributes
    )

    previous_span = _current_span
    _current_span = span

    try:
        yield span
        span.set_status("OK")
    except Exception as e:
        if record_exception:
            span.record_exception(e)
        raise
    finally:
        span.end()
        _current_span = previous_span


def query_traces(sql: str) -> List[Dict[str, Any]]:
    """Execute a SQL query against the traces database."""
    conn = _get_connection()
    if conn is None:
        return []

    try:
        result = conn.execute(sql).fetchall()
        columns = [desc[0] for desc in conn.description]
        return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return []


def get_slow_operations(threshold_ms: float = 1000, limit: int = 20) -> List[Dict[str, Any]]:
    """Get operations slower than threshold."""
    return query_traces(f"""
        SELECT name, duration_ms, start_time, status, user_id,
               json_extract_string(attributes, '$.error_message') as error
        FROM spans
        WHERE duration_ms > {threshold_ms}
        ORDER BY duration_ms DESC
        LIMIT {limit}
    """)


def get_errors(hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent errors."""
    return query_traces(f"""
        SELECT name, error_message, start_time, duration_ms, user_id, trace_id
        FROM spans
        WHERE status = 'ERROR'
          AND start_time > now() - INTERVAL '{hours} hours'
        ORDER BY start_time DESC
        LIMIT {limit}
    """)


def get_stats(hours: int = 24) -> Dict[str, Any]:
    """Get trace statistics."""
    result = query_traces(f"""
        SELECT
            COUNT(*) as total_spans,
            COUNT(CASE WHEN status = 'ERROR' THEN 1 END) as error_count,
            AVG(duration_ms) as avg_duration_ms,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as p50_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_ms,
            MAX(duration_ms) as max_duration_ms
        FROM spans
        WHERE start_time > now() - INTERVAL '{hours} hours'
    """)
    return result[0] if result else {}


def get_stats_by_operation(hours: int = 24) -> List[Dict[str, Any]]:
    """Get stats grouped by operation name."""
    return query_traces(f"""
        SELECT
            name,
            COUNT(*) as count,
            AVG(duration_ms) as avg_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_ms,
            MAX(duration_ms) as max_ms,
            COUNT(CASE WHEN status = 'ERROR' THEN 1 END) as errors
        FROM spans
        WHERE start_time > now() - INTERVAL '{hours} hours'
        GROUP BY name
        ORDER BY count DESC
    """)


def get_trace(trace_id: str) -> List[Dict[str, Any]]:
    """Get all spans for a trace."""
    return query_traces(f"""
        SELECT span_id, parent_span_id, name, start_time, duration_ms, status, attributes
        FROM spans
        WHERE trace_id = '{trace_id}'
        ORDER BY start_time
    """)


def cleanup_old_traces():
    """Delete traces older than retention period."""
    conn = _get_connection()
    if conn is None:
        return

    try:
        conn.execute(f"""
            DELETE FROM spans
            WHERE start_time < now() - INTERVAL '{TRACES_RETENTION_DAYS} days'
        """)
        logger.info(f"Cleaned up traces older than {TRACES_RETENTION_DAYS} days")
    except Exception as e:
        logger.error(f"Failed to cleanup traces: {e}")
