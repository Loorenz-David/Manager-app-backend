from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.notifications.pin_cleanup import cleanup_task_pins
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_delete_message
from beyo_manager.services.commands.items.cancel_upholstery_requirements import (
    cancel_unfinished_item_requirements_in_session,
    lock_and_filter_items_without_active_tasks,
)
from beyo_manager.services.commands.tasks.requests import parse_terminal_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def delete_task(ctx: ServiceContext) -> dict:
    request = parse_terminal_task_request(ctx.incoming_data)
    cancelled_item_upholstery_ids: list[str] = []

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.client_id,
            )
        )
        task = result.scalar_one_or_none()
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
        cancellable_item_ids = await lock_and_filter_items_without_active_tasks(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_ids=linked_item_ids,
            excluding_task_id=task.client_id,
        )

        # Refresh and lock the target after the deterministic item/task locking
        # pass. This also covers tasks that have no linked items.
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
        if task.is_deleted:
            raise ConflictError("Task is already deleted.")

        now = datetime.now(timezone.utc)
        cancelled = await cancel_unfinished_item_requirements_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_ids=cancellable_item_ids,
            actor_id=ctx.user_id,
            now=now,
        )
        cancelled_item_upholstery_ids = sorted(
            {row.item_upholstery_id for row in cancelled}
        )

        task.is_deleted = True
        task.deleted_at = now
        task.deleted_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.DELETED,
            description=build_delete_message(username, "task", "workspace"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )
        await cleanup_task_pins(ctx.session, task.client_id)

    events = [build_workspace_event(task, "task:deleted")]
    events.extend(
        WorkspaceEvent(
            event_name="item:upholstery-requirement-state-changed",
            client_id=item_upholstery_id,
            workspace_id=ctx.workspace_id,
            extra={
                "new_state": ItemUpholsteryRequirementStateEnum.FAILED.value
            },
        )
        for item_upholstery_id in cancelled_item_upholstery_ids
    )
    await event_bus.dispatch(events)
    return {"client_id": task.client_id}
