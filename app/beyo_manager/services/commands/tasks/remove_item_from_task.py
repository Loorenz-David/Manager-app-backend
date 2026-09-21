from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_delete_message
from beyo_manager.services.commands.stock_report._locks import (
    lock_stock_report_items,
    lock_stock_task_assignments,
    lock_tasks,
)
from beyo_manager.services.commands.stock_report._remove_assignment import (
    remove_assignment,
)
from beyo_manager.services.commands.tasks.requests import parse_remove_item_from_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def remove_item_from_task(ctx: ServiceContext) -> dict:
    request = parse_remove_item_from_task_request(ctx.incoming_data)
    stock_events: list = []

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(TaskItem).where(
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.task_id == request.task_id,
                TaskItem.item_id == request.item_id,
                TaskItem.removed_at.is_(None),
            )
        )
        task_item = result.scalar_one_or_none()
        if task_item is None:
            raise NotFound("Task item not found.")

        # MC-14 row 2 (master plan §6.1b, this file loads no Task today): lock the
        # Task before the TaskItem write, ahead of any stock-report lock (MC-1
        # order: items -> tasks -> rows -> assignments).
        await lock_tasks(ctx.session, ctx.workspace_id, {request.task_id})

        if task_item.role == TaskItemRoleEnum.PRIMARY:
            # Unlocked discovery — decides only which rows and assignments to lock.
            discovered = (
                (
                    await ctx.session.execute(
                        select(StockTaskAssignment).where(
                            StockTaskAssignment.workspace_id == ctx.workspace_id,
                            StockTaskAssignment.task_id == request.task_id,
                            StockTaskAssignment.item_id == request.item_id,
                            StockTaskAssignment.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            row_ids = {assignment.stock_report_item_id for assignment in discovered}
            await lock_stock_report_items(ctx.session, ctx.workspace_id, row_ids)
            locked_assignments = await lock_stock_task_assignments(
                ctx.session, ctx.workspace_id, {a.client_id for a in discovered}
            )
            for client_id in sorted(locked_assignments):
                assignment = locked_assignments[client_id]
                if assignment.is_deleted:
                    continue  # re-read after lock: a concurrent delete won here
                stock_events.extend(
                    await remove_assignment(
                        ctx.session,
                        assignment,
                        workspace_id=ctx.workspace_id,
                        actor_user_id=ctx.user_id,
                        now=ctx.now,
                        trigger="remove_item_from_task",
                    )
                )
        # RELATED -> nothing (no assignment can exist for a non-PRIMARY link).

        task_item.removed_at = datetime.now(timezone.utc)
        task_item.removed_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task_item.task_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_delete_message(username, "item", "task"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    events = [
        WorkspaceEvent(
            event_name="task:updated",
            client_id=task_item.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ]
    events.extend(stock_events)
    await event_bus.dispatch(events)
    return {"client_id": task_item.client_id}
