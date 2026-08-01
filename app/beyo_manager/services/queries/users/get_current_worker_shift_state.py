import logging
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.serializers import (
    pause_reason_reference_is_unresolved,
    serialize_current_worker_shift_state,
)
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.worker_shift_access import (
    resolve_worker_shift_target,
)


logger = logging.getLogger(__name__)


async def load_current_worker_shift_state(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
) -> dict:
    """The worker's live shift state, already serialized — no access check.

    The caller decides who is allowed to see this. `get_current_worker_shift_state`
    resolves the target through the access rules first; the realtime emitter addresses
    the worker's own room and needs no such check. Both go through here so the socket
    payload and the HTTP response can never drift apart.
    """
    now = datetime.now(timezone.utc)
    current_pause_reason = aliased(PauseReason)
    declared_pause_reason = aliased(PauseReason)
    shift_marker = aliased(UserShiftStateRecord)
    shift_started_at = (
        select(func.max(shift_marker.entered_at))
        .where(
            shift_marker.workspace_id == workspace_id,
            shift_marker.user_id == user_id,
            shift_marker.state == UserShiftStateEnum.STARTED_SHIFT,
            shift_marker.entered_at <= now,
        )
        .scalar_subquery()
    )

    row = (
        await session.execute(
            select(
                UserShiftStateRecord,
                current_pause_reason,
                UserDeclaredStateRecord,
                declared_pause_reason,
                shift_started_at.label("shift_started_at"),
            )
            .outerjoin(
                current_pause_reason,
                and_(
                    current_pause_reason.workspace_id == workspace_id,
                    current_pause_reason.client_id == UserShiftStateRecord.reason,
                ),
            )
            .outerjoin(
                UserDeclaredStateRecord,
                and_(
                    UserDeclaredStateRecord.workspace_id
                    == UserShiftStateRecord.workspace_id,
                    UserDeclaredStateRecord.user_id == UserShiftStateRecord.user_id,
                    UserDeclaredStateRecord.exited_at.is_(None),
                ),
            )
            .outerjoin(
                declared_pause_reason,
                and_(
                    declared_pause_reason.workspace_id == workspace_id,
                    declared_pause_reason.client_id
                    == UserDeclaredStateRecord.pause_reason_id,
                ),
            )
            .where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).one_or_none()

    if row is None:
        return serialize_current_worker_shift_state(user_id=user_id, current=None)

    current, pause_reason, declared_record, declared_reason, started_at = row
    if pause_reason_reference_is_unresolved(current, pause_reason):
        logger.warning(
            "worker_shift.current_state_unresolved_pause_reason | "
            "workspace_id=%s user_id=%s shift_record_id=%s pause_reason_id=%s",
            workspace_id,
            user_id,
            current.client_id,
            current.reason,
        )
    return serialize_current_worker_shift_state(
        user_id=user_id,
        current=current,
        shift_started_at=started_at,
        pause_reason=pause_reason,
        declared_record=declared_record,
        declared_pause_reason=declared_reason,
    )


async def get_current_worker_shift_state(ctx: ServiceContext) -> dict:
    user_id = await resolve_worker_shift_target(ctx, ctx.query_params.get("user_id"))
    return await load_current_worker_shift_state(ctx.session, ctx.workspace_id, user_id)
