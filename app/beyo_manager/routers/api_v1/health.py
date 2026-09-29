import asyncio
import logging

import redis as _redis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from beyo_manager.config import settings
from beyo_manager.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# A dependency that does not answer within this time counts as down, so a hung
# database or Redis cannot hang the health check itself.
_CHECK_TIMEOUT_SECONDS = 3


@router.get("/live")
async def liveness_check() -> JSONResponse:
    """The API process is serving requests. Checks no dependency on purpose: this is
    what Docker's health check calls, and a database or Redis outage is not a reason
    to call the API process itself broken. Not counted as activity (sleep mode)."""
    return JSONResponse(content={"status": "ok"})


async def _check_db() -> None:
    async for session in get_db():
        await session.execute(text("SELECT 1"))


def _check_redis() -> None:
    client = _redis.from_url(
        settings.redis_url,
        socket_connect_timeout=_CHECK_TIMEOUT_SECONDS,
        socket_timeout=_CHECK_TIMEOUT_SECONDS,
    )
    try:
        client.ping()
    finally:
        client.close()


@router.get("")
async def health_check() -> JSONResponse:
    """Readiness: the database and Redis both answer. 503 when either does not.
    Error details go to the log only; this endpoint is public."""
    status: dict = {"status": "ok", "services": {}}
    ok = True

    checks = (
        ("db", _check_db()),
        ("redis", asyncio.to_thread(_check_redis)),
    )
    for name, check in checks:
        try:
            await asyncio.wait_for(check, timeout=_CHECK_TIMEOUT_SECONDS)
            status["services"][name] = "ok"
        except Exception as exc:
            logger.warning("health_check_failed | service=%s error=%r", name, exc)
            status["services"][name] = f"error: {type(exc).__name__}"
            ok = False

    status["status"] = "ok" if ok else "degraded"
    log_health(status["services"].get("db", "unknown"), status["services"].get("redis", "unknown"))
    return JSONResponse(content=status, status_code=200 if ok else 503)


# Observability runtime health logging
from beyo_manager.core.observability.runtime import log_health
