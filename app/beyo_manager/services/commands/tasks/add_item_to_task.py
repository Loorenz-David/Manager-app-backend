from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_create_message
from beyo_manager.services.commands.tasks.requests import parse_add_item_to_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def add_item_to_task(ctx: ServiceContext) -> dict:
    request = parse_add_item_to_task_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.task_id,
                Task.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")

        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.item_id,
                Item.is_deleted.is_(False),
            )
        )
        item = item_result.scalar_one_or_none()
        if item is None:
            raise NotFound("Item not found.")

        if request.role == TaskItemRoleEnum.PRIMARY:
            primary_result = await ctx.session.execute(
                select(TaskItem).where(
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.task_id == request.task_id,
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
                    TaskItem.removed_at.is_(None),
                )
            )
            if primary_result.scalar_one_or_none() is not None:
                raise ConflictError("Task already has an active primary item.")

        existing_result = await ctx.session.execute(
            select(TaskItem).where(
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.task_id == request.task_id,
                TaskItem.item_id == request.item_id,
                TaskItem.removed_at.is_(None),
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            raise ConflictError("Item already active on this task.")

        task_item = TaskItem(
            workspace_id=ctx.workspace_id,
            task_id=request.task_id,
            item_id=request.item_id,
            role=request.role,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(task_item)
        await ctx.session.flush()

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task_item.task_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_create_message(username, "item", "task"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"client_id": task_item.client_id}
