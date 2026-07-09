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

    # The root logger stays at INFO so unrelated domains don't get noisy. Shopify's
    # `.debug(...)` calls are otherwise filtered out before they reach any handler
    # regardless of SHOPIFY_INTEGRATION_DEBUG_LOGS, since that setting only gates
    # *whether* the call site calls `.debug(...)` — it does not raise the logger's
    # own level. Elevate just the Shopify logger namespaces here so the setting
    # actually has an effect.
    if settings.shopify_integration_debug_logs:
        for _namespace in (
            "beyo_manager.routers.api_v1.shopify",
            "beyo_manager.routers.api_v1.shopify_webhooks",
            "beyo_manager.services.commands.shopify",
            "beyo_manager.services.queries.shopify",
            "beyo_manager.services.tasks.shopify",
            "beyo_manager.services.infra.shopify",
        ):
            logging.getLogger(_namespace).setLevel(logging.DEBUG)

    _CONFIGURED = True


def log_event(event_type: str, **extra: object) -> None:
    logger = logging.getLogger("app")
    payload = {"event_type": event_type, "service": settings.redis_key_prefix}
    payload.update(extra)
    logger.info(event_type, extra=payload)
