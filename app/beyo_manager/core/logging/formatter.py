from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from .context import get_log_context


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

        for key in ("service", "path", "method", "status_code", "error", "db_health", "redis_health"):
            value = getattr(record, key, None)
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

        return json.dumps(payload, ensure_ascii=True)
