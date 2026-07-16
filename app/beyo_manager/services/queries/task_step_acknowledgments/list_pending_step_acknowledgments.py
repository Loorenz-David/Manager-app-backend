from sqlalchemy import and_, select

from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.step_record_payload import (
    build_step_record_payload,
    load_step_with_latest_record,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _serialize_acknowledgment(
    ack: TaskStepAcknowledgment,
    *,
    worker: User | None,
    created_by: User | None,
) -> dict:
    return {
        "client_id": ack.client_id,
        "step_id": ack.step_id,
        "task_id": ack.task_id,
        # Free-text reassignment note; the frontend truncates it via the notes system.
        "reason": ack.reason,
        "worker": serialize_user_working_section_member(worker) if worker else None,
        "created_by": serialize_user_working_section_member(created_by) if created_by else None,
        "first_seen_at": ack.first_seen_at.isoformat() if ack.first_seen_at else None,
        "acknowledged_at": ack.acknowledged_at.isoformat() if ack.acknowledged_at else None,
        "created_at": ack.created_at.isoformat(),
    }


async def list_pending_step_acknowledgments(ctx: ServiceContext) -> dict:
    """The calling worker's unacknowledged reassignment obligations.

    Each item carries the same full resume-card payload as
    ``build_step_record_payload`` (step, task, item, item_images, …) plus the
    reassignment fields (``acknowledgment``) the frontend needs to render and
    acknowledge the row. ``cases_summary`` is included because the viewer here
    is the step's own worker.
    """
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    ack_result = await ctx.session.execute(
        select(TaskStepAcknowledgment)
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == TaskStepAcknowledgment.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(
            TaskStepAcknowledgment.workspace_id == ctx.workspace_id,
            TaskStepAcknowledgment.worker_id == ctx.user_id,
            TaskStepAcknowledgment.acknowledged_at.is_(None),
            TaskStepAcknowledgment.is_deleted.is_(False),
        )
        .order_by(
            TaskStepAcknowledgment.created_at.desc(),
            TaskStepAcknowledgment.client_id.desc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )
    acks = ack_result.scalars().all()
    has_more = len(acks) > limit
    page = acks[:limit]

    # Batch-load the users referenced by the page (worker + creator).
    user_ids = {
        uid
        for ack in page
        for uid in (ack.worker_id, ack.created_by_id)
        if uid
    }
    users_map: dict[str, User] = {}
    if user_ids:
        users_result = await ctx.session.execute(
            select(User).where(User.client_id.in_(user_ids))
        )
        users_map = {user.client_id: user for user in users_result.scalars().all()}

    items: list[dict] = []
    for ack in page:
        step = await load_step_with_latest_record(ctx, ack.step_id)
        if step is None:
            continue
        payload = await build_step_record_payload(ctx, step)
        payload["acknowledgment"] = _serialize_acknowledgment(
            ack,
            worker=users_map.get(ack.worker_id),
            created_by=users_map.get(ack.created_by_id) if ack.created_by_id else None,
        )
        items.append(payload)

    return {
        "acknowledgments": items,
        "acknowledgments_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
