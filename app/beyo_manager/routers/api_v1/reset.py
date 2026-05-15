from fastapi import APIRouter, Header, HTTPException

from beyo_manager.models.database import get_db_session
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.reset.reset_app import reset_app
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service
from beyo_manager.config import settings

router = APIRouter()


@router.delete("")
async def reset_route(
    workspace_id: str,
    delete_orphan_bootstrap_users: bool = True,
    x_reset_secret: str | None = Header(default=None, alias="X-Reset-Secret"),
):
    # Reset is disabled if RESET_SECRET env var is empty/not set.
    if not settings.reset_secret:
        raise HTTPException(status_code=501, detail="Reset endpoint is disabled. Set RESET_SECRET to enable.")

    if not x_reset_secret or x_reset_secret != settings.reset_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing reset secret.")

    session_iter = get_db_session()
    session = await anext(session_iter)
    try:
        ctx = ServiceContext(
            identity={"workspace_id": workspace_id},
            incoming_data={"delete_orphan_bootstrap_users": delete_orphan_bootstrap_users},
            session=session,
        )
        outcome = await run_service(reset_app, ctx)
        if not outcome.success:
            return build_err(outcome.error)
        return build_ok(outcome.data, warnings=[])
    finally:
        await session_iter.aclose()
