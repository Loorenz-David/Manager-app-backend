from datetime import date, datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

# Public shared API of this module (imported by the sibling worker-stats services).
TIME_STATES = (
    TaskStepStateEnum.WORKING,
    TaskStepStateEnum.PAUSED,
    TaskStepStateEnum.ENDED_SHIFT,
)


# Upper bound on a requested range span, to keep aggregate reads bounded.
_MAX_RANGE_DAYS = 366


def _parse_iso_date(raw: str, field: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"{field} must be a valid ISO date in YYYY-MM-DD format.") from exc


def resolve_work_date(raw_work_date: str | None) -> date:
    if not raw_work_date:
        return datetime.now(timezone.utc).date()
    return _parse_iso_date(raw_work_date, "work_date")


def resolve_date_range(query_params: dict) -> tuple[date, date]:
    """Inclusive ``[date_from, date_to]`` from query params; both default to UTC today.

    Raises ``ValidationError`` on unparseable dates, an inverted range, or a span wider
    than ``_MAX_RANGE_DAYS``.
    """
    today = datetime.now(timezone.utc).date()
    raw_from = query_params.get("date_from")
    raw_to = query_params.get("date_to")
    date_from = _parse_iso_date(raw_from, "date_from") if raw_from else today
    date_to = _parse_iso_date(raw_to, "date_to") if raw_to else today
    if date_to < date_from:
        raise ValidationError("date_to must be on or after date_from.")
    if (date_to - date_from).days + 1 > _MAX_RANGE_DAYS:
        raise ValidationError(f"date range cannot exceed {_MAX_RANGE_DAYS} days.")
    return date_from, date_to


def _worker_role_filter():
    # Specializations remain workers at the base workspace-role level.
    return Role.name == RoleNameEnum.WORKER.value


def _worker_membership_query(ctx: ServiceContext, columns):
    return (
        select(*columns)
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
        .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
        .join(Role, Role.client_id == WorkspaceRole.role_id)
        .where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.is_active.is_(True),
            _worker_role_filter(),
        )
    )


async def load_worker_page(ctx: ServiceContext) -> tuple[list[User], dict]:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    total_result = await ctx.session.execute(
        _worker_membership_query(ctx, [func.count(User.client_id.distinct())])
    )
    total = total_result.scalar() or 0

    workers_result = await ctx.session.execute(
        _worker_membership_query(ctx, [User])
        .order_by(User.username.asc())
        .offset(offset)
        .limit(limit + 1)
    )
    workers = workers_result.scalars().all()
    has_more = len(workers) > limit

    return workers[:limit], {
        "has_more": has_more,
        "limit": limit,
        "offset": offset,
        "total": total,
    }


async def count_completed_steps(
    session: AsyncSession,
    workspace_id: str,
    user_ids: list[str],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, int]:
    """Per-worker count of steps completed **during a recorded shift** in
    ``[window_start, window_end)``.

    Counts ``COMPLETED`` ``StepStateRecord`` rows credited to each worker
    (``COALESCE(credited_user_id, created_by_id)``), joined to a live step — but only when
    the completion's ``entered_at`` falls inside one of the worker's recorded
    ``UserShiftStateRecord`` intervals. This scopes the count to the same recorded-shift
    reality as the linear-timeline buckets, so a day with no recorded shift contributes
    zero completions (rather than the raw calendar-range total). Shift-record bounds are
    inclusive on both ends, so a completion landing exactly on the ``ended_shift`` marker
    (its zero-duration timestamp) still counts.
    """
    if not user_ids:
        return {}
    credited = func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)
    on_recorded_shift = (
        select(UserShiftStateRecord.client_id)
        .where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == credited,
            UserShiftStateRecord.entered_at <= StepStateRecord.entered_at,
            or_(
                UserShiftStateRecord.exited_at.is_(None),
                UserShiftStateRecord.exited_at >= StepStateRecord.entered_at,
            ),
        )
        .exists()
    )
    rows = await session.execute(
        select(credited.label("user_id"), func.count(StepStateRecord.client_id).label("completed"))
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.workspace_id == workspace_id,
            StepStateRecord.is_deleted.is_(False),
            credited.in_(user_ids),
            StepStateRecord.state == TaskStepStateEnum.COMPLETED,
            StepStateRecord.entered_at >= window_start,
            StepStateRecord.entered_at < window_end,
            on_recorded_shift,
        )
        .group_by(credited)
    )
    return {row.user_id: int(row.completed) for row in rows.all()}
