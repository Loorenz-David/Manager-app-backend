from __future__ import annotations

import logging
import logging.config

from beyo_manager.config import settings


_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "beyo_manager.core.logging.formatter.StructuredJsonFormatter",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )
    _CONFIGURED = True


def log_event(event_type: str, **extra: object) -> None:
    logger = logging.getLogger("app")
    payload = {"event_type": event_type, "service": settings.redis_key_prefix}
    payload.update(extra)
    logger.info(event_type, extra=payload)
