from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from .context import get_log_context

# Everything `logging` itself puts on a record. Whatever is left over came from a
# caller's `extra={...}` and is emitted as-is — this used to be a fixed whitelist
# of seven keys, which silently dropped every other field a caller passed.
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "duration_ms",
        "event_type",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event_type": getattr(record, "event_type", record.msg),
            "message": record.getMessage(),
            "duration_ms": getattr(record, "duration_ms", None),
        }
        payload.update(get_log_context())

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            if value is not None:
                payload[key] = value

        # This formatter does not delegate to logging.Formatter.format(), so
        # exc_info/stack_info would otherwise be dropped entirely and
        # logger.exception(...) would emit a JSON line with no traceback.
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["exc_type"] = getattr(exc_type, "__name__", str(exc_type))
            payload["exc_message"] = str(exc_value)
            payload["traceback"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["traceback"] = record.exc_text

        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        # `default=str` because pass-through extras are arbitrary caller values:
        # an enum, a datetime or a model object must not make the formatter raise
        # and take the log line (or the request) down with it.
        return json.dumps(payload, ensure_ascii=True, default=str)
