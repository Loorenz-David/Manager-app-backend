from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from beyo_manager.config import settings
from beyo_manager.models.database import get_db

router = APIRouter()


@router.get("")
async def health_check() -> JSONResponse:
    status: dict = {"status": "ok", "services": {}}
    ok = True

    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
        status["services"]["db"] = "ok"
    except Exception as exc:
        status["services"]["db"] = f"error: {exc}"
        ok = False

    try:
        import redis as _r
        _r.from_url(settings.redis_url).ping()
        status["services"]["redis"] = "ok"
    except Exception as exc:
        status["services"]["redis"] = f"error: {exc}"
        ok = False

    status["status"] = "ok" if ok else "degraded"
    log_health(status["services"].get("db", "unknown"), status["services"].get("redis", "unknown"))
    return JSONResponse(content=status, status_code=200 if ok else 503)


# Observability runtime health logging
from beyo_manager.core.observability.runtime import log_health
