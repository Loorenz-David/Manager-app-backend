from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims, require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.notifications.mark_notifications_read import mark_notifications_read
from beyo_manager.services.commands.notifications.pin_notification import pin_notification
from beyo_manager.services.commands.notifications.register_push_subscription import register_push_subscription
from beyo_manager.services.commands.notifications.unpin_notification import unpin_notification
from beyo_manager.services.commands.notifications.unregister_push_subscription import unregister_push_subscription
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.notifications.get_unread_notification_count import get_unread_notification_count
from beyo_manager.services.queries.notifications.list_notifications import list_notifications
from beyo_manager.services.run_service import run_service

router = APIRouter()


class PushSubscriptionBody(BaseModel):
    endpoint:     str
    p256dh:       str
    auth:         str
    device_label: str | None = None


class PinBody(BaseModel):
    entity_type:      str
    entity_client_id: str


class MarkReadBody(BaseModel):
    notification_client_ids: list[str] | None = None
    mark_all_read:           bool = False


async def _run(command, incoming_data: dict, claims: dict, session: AsyncSession):
    outcome = await run_service(
        command,
        ServiceContext(identity=claims, incoming_data=incoming_data, session=session),
    )
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


# ── List / unread count ──────────────────────────────────────────────────────

@router.get("")
async def list_notifications_route(
    unread_only: bool = False,
    limit: int = 30,
    before_client_id: str | None = None,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_notifications,
        {"unread_only": unread_only, "limit": limit, "before_client_id": before_client_id},
        claims,
        session,
    )


@router.get("/unread-count")
async def unread_count_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_unread_notification_count, {}, claims, session)


@router.post("/mark-read")
async def mark_read_route(
    body: MarkReadBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(mark_notifications_read, body.model_dump(), claims, session)


# ── Push subscriptions ───────────────────────────────────────────────────────

@router.post("/push-subscription")
async def subscribe_route(
    body: PushSubscriptionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(register_push_subscription, body.model_dump(), claims, session)


@router.delete("/push-subscription")
async def unsubscribe_route(
    body: PushSubscriptionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(unregister_push_subscription, body.model_dump(), claims, session)


@router.get("/vapid-public-key")
async def vapid_public_key_route():
    """Public endpoint — no auth required. Frontend fetches before login."""
    return build_ok({"public_key": getattr(settings, "vapid_public_key", "")})


# ── Pins ─────────────────────────────────────────────────────────────────────

@router.post("/pins")
async def pin_route(
    body: PinBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(pin_notification, body.model_dump(), claims, session)


@router.delete("/pins")
async def unpin_route(
    body: PinBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(unpin_notification, body.model_dump(), claims, session)
