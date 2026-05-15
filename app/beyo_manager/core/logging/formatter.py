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

        return json.dumps(payload, ensure_ascii=True)
