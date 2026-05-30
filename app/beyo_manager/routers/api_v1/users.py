from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims, require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.users.deactivate_user import deactivate_user
from beyo_manager.services.commands.users.record_view_events import record_view_events
from beyo_manager.services.commands.users.update_self_password import update_self_password
from beyo_manager.services.commands.users.update_self_profile import update_self_profile
from beyo_manager.services.commands.users.update_user_admin import update_user_admin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.get_current_view import get_current_view
from beyo_manager.services.queries.users.get_live_workspace_presence import get_live_workspace_presence
from beyo_manager.services.queries.users.get_self_profile import get_self_profile
from beyo_manager.services.queries.users.get_user_admin import get_user_admin
from beyo_manager.services.queries.users.list_self_view_records import list_self_view_records
from beyo_manager.services.queries.users.list_user_view_records import list_user_view_records
from beyo_manager.services.queries.users.list_users import list_users
from beyo_manager.services.run_service import run_service

router = APIRouter()


class UpdateSelfProfileBody(BaseModel):
    email: str | None = None
    phone_number: str | None = None
    profile_picture: str | None = None


class UpdateSelfPasswordBody(BaseModel):
    current_password: str
    new_password: str


class UpdateUserAdminBody(BaseModel):
    email: str | None = None
    phone_number: str | None = None
    profile_picture: str | None = None
    salary_per_hour_before_tax: str | None = None
    salary_per_hour_after_tax: str | None = None


class RecordViewEventsBody(BaseModel):
    records: list[dict]


@router.get("/me")
async def get_self_profile_route(
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_self_profile, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/me/view-records")
async def list_self_view_records_route(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
        query_params={"limit": str(limit), "offset": str(offset)},
    )
    outcome = await run_service(list_self_view_records, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/me/view-records/current")
async def get_current_view_route(
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_current_view, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/me")
async def update_self_profile_route(
    body: UpdateSelfProfileBody,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(exclude_unset=True),
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_self_profile, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/me/password")
async def update_self_password_route(
    body: UpdateSelfPasswordBody,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_self_password, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/me/view-records")
async def record_view_events_route(
    body: RecordViewEventsBody,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(record_view_events, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/live")
async def get_live_workspace_presence_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_live_workspace_presence, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def list_users_route(
    q: str | None = Query(None),
    string_filters: str | None = Query(None),
    role: str | None = Query(None),
    working_sections: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    compact: bool = Query(False),
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
        query_params={
            "q": q,
            "string_filters": string_filters,
            "role": role,
            "working_sections": working_sections,
            "limit": str(limit),
            "offset": str(offset),
            "compact": str(compact),
        },
    )
    outcome = await run_service(list_users, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{user_client_id}")
async def get_user_admin_route(
    user_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_user_admin, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{user_client_id}")
async def update_user_admin_route(
    user_client_id: str,
    body: UpdateUserAdminBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_user_admin, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{user_client_id}/deactivate")
async def deactivate_user_route(
    user_client_id: str,
    claims: dict = Depends(require_roles([ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(deactivate_user, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{user_client_id}/view-records")
async def list_user_view_records_route(
    user_client_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id},
        identity=claims,
        session=session,
        query_params={"limit": str(limit), "offset": str(offset)},
    )
    outcome = await run_service(list_user_view_records, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
