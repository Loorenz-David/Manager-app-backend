from __future__ import annotations

from beyo_manager.core.logging.config import log_event


def log_startup() -> None:
    log_event("runtime.startup")


def log_shutdown() -> None:
    log_event("runtime.shutdown")


def log_health(db_health: str, redis_health: str) -> None:
    log_event("runtime.health", db_health=db_health, redis_health=redis_health)
