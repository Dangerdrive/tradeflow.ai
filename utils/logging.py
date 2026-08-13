"""Logging estruturado (JSON) com suporte a correlation ID.

Uso:
    from utils.logging import setup_logging, set_correlation_id

    setup_logging("INFO")
    set_correlation_id("req-123")   # opcional, propaga via ContextVar
    logger = logging.getLogger("tradeflow")
    logger.info("evento", extra={"campo": "valor"})
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# ContextVar permite propagar o correlation ID sem passá-lo manualmente.
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

_RESERVED_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Formata registros como JSON de linha única, sem PII por padrão."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
        }
        # Campos extras fornecidos via `extra={...}`.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configura o logging estruturado na raiz (stdout)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def set_correlation_id(value: str | None) -> None:
    """Define o correlation ID do contexto atual."""
    correlation_id.set(value)
