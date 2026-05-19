from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_delete_message
from beyo_manager.services.commands.tasks.requests import parse_remove_item_from_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def remove_item_from_task(ctx: ServiceContext) -> dict:
    request = parse_remove_item_from_task_request(ctx.incoming_data)

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

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=task_item.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"client_id": task_item.client_id}
