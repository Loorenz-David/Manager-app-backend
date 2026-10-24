from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import (
    build_create_message,
    build_restore_message,
)
from beyo_manager.services.commands.items.cancel_upholstery_requirements import (
    lock_and_filter_items_without_active_tasks,
)
from beyo_manager.services.commands.items.create_item_upholstery import (
    ensure_item_upholstery_in_session,
)
from beyo_manager.services.commands.task_steps._pause_task_working_steps import (
    pause_task_working_steps_in_session,
)
from beyo_manager.services.commands.tasks.requests import parse_terminal_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.events.worker_shift_realtime import emit_steps_paused


async def restore_task(ctx: ServiceContext) -> dict:
    """Bring a soft-deleted task back, with the upholstery need its deletion cancelled.

    `delete_task` fails the unfinished upholstery requirement of every item no other
    active task holds, stamping `failed_at` with the task's own `deleted_at`. That shared
    timestamp is how a restore recognises exactly those requirements. Each one is
    revived the way any ended upholstery context is: archived and replaced by a fresh
    context whose requirement is re-checked against today's stock (`available` or
    `needs_ordering`). An item whose upholstery moved on since the deletion is left alone.

    A task deleted before `delete_task` paused working steps may still hold a step whose
    WORKING record never closed; it is paused as of the deletion, so the deleted period
    does not count as work. Steps are not resumed — the worker does that.

    Stock-report assignments and pins removed by the deletion are not restored.
    """
    request = parse_terminal_task_request(ctx.incoming_data)
    item_events: list[WorkspaceEvent] = []
    paused_step_ids: list[str] = []

    async with maybe_begin(ctx.session):
        task = (
            await ctx.session.execute(
                select(Task).where(
                    Task.workspace_id == ctx.workspace_id,
                    Task.client_id == request.client_id,
                )
            )
        ).scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")

        linked_item_ids = list(
            (
                await ctx.session.execute(
                    select(TaskItem.item_id)
                    .where(
                        TaskItem.workspace_id == ctx.workspace_id,
                        TaskItem.task_id == task.client_id,
                        TaskItem.removed_at.is_(None),
                    )
                    .distinct()
                    .order_by(TaskItem.item_id.asc())
                )
            ).scalars()
        )
        # Same lock order as delete_task (Items -> Task) so the two cannot deadlock.
        # An item another active task already holds keeps that task's upholstery.
        revivable_item_ids = await lock_and_filter_items_without_active_tasks(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_ids=linked_item_ids,
            excluding_task_id=task.client_id,
        )

        task = (
            await ctx.session.execute(
                select(Task)
                .where(
                    Task.workspace_id == ctx.workspace_id,
                    Task.client_id == request.client_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        if not task.is_deleted:
            raise ConflictError("Task is not deleted.")

        deleted_at = task.deleted_at
        task.is_deleted = False
        task.deleted_at = None
        task.deleted_by_id = None
        task.updated_at = datetime.now(timezone.utc)
        task.updated_by_id = ctx.user_id

        username = ctx.identity.get("username")
        # UPDATED on `is_deleted` rather than a new change type: the change type is a
        # Postgres enum, and a restore is exactly the flag flipping back.
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_restore_message(username, f"task #{task.task_scalar_id}"),
            field_name="is_deleted",
            from_value={"is_deleted": True},
            to_value={"is_deleted": False},
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

        if deleted_at is not None:
            paused_step_ids = await pause_task_working_steps_in_session(
                ctx, task, paused_at=deleted_at
            )
            for item_id in revivable_item_ids:
                item_events.extend(
                    await _revive_upholstery_need(ctx, item_id=item_id, deleted_at=deleted_at)
                )

    # `task:updated` already refreshes the detail and every task list in all apps.
    await event_bus.dispatch([build_workspace_event(task, "task:updated"), *item_events])
    await emit_steps_paused(ctx.workspace_id, paused_step_ids)
    return {"client_id": task.client_id}


async def _revive_upholstery_need(
    ctx: ServiceContext,
    *,
    item_id: str,
    deleted_at: datetime,
) -> list[WorkspaceEvent]:
    current_rows = (
        await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id == item_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    if len(current_rows) != 1 or current_rows[0].active_requirement_id is None:
        return []
    current = current_rows[0]

    requirement = (
        await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.client_id == current.active_requirement_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    # Only the requirement this task's deletion failed — not one failed for any other reason.
    if (
        requirement is None
        or requirement.state != ItemUpholsteryRequirementStateEnum.FAILED
        or requirement.failed_at != deleted_at
    ):
        return []

    item_upholstery_id, _created = await ensure_item_upholstery_in_session(
        ctx,
        item_id=item_id,
        data={
            "upholstery_id": current.upholstery_id,
            "name": current.name,
            "code": current.code,
            # The requirement's amount is the need that was cancelled; the context's
            # own amount can lag behind a later quantity edit.
            "amount_meters": requirement.amount_meters,
            "source": current.source,
            "time_to_fix_in_seconds": current.time_to_fix_in_seconds,
        },
    )

    username = ctx.identity.get("username")
    upholstery_target = f"upholstery '{current.name}'" if current.name else "upholstery"
    await _create_history_record_in_session(
        session=ctx.session,
        entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
        entity_client_id=item_upholstery_id,
        change_type=HistoryRecordChangeTypeEnum.CREATED,
        description=build_create_message(username, upholstery_target, "item"),
        field_name=None,
        from_value=None,
        to_value=None,
        created_by_id=ctx.user_id,
        username_snapshot=username,
    )

    # The same pair `create_item_upholstery` announces for a new context.
    return [
        WorkspaceEvent(
            event_name="item:updated",
            client_id=item_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
        WorkspaceEvent(
            event_name="item:upholstery-created",
            client_id=item_upholstery_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ]
