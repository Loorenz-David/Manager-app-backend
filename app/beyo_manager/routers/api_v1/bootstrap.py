from fastapi import APIRouter, Header, HTTPException

from beyo_manager.models.database import get_db_session
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.bootstrap.bootstrap_app import bootstrap_app
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service
from beyo_manager.config import settings

router = APIRouter()


@router.post("")
async def bootstrap_route(
    x_bootstrap_secret: str | None = Header(default=None, alias="X-Bootstrap-Secret"),
):
    if not settings.bootstrap_secret or not x_bootstrap_secret or x_bootstrap_secret != settings.bootstrap_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing bootstrap secret.")

    session_iter = get_db_session()
    session = await anext(session_iter)
    try:
        ctx = ServiceContext(identity={}, incoming_data={}, session=session)
        outcome = await run_service(bootstrap_app, ctx)
        if not outcome.success:
            return build_err(outcome.error)
        return build_ok(outcome.data, warnings=[])
    finally:
        await session_iter.aclose()
