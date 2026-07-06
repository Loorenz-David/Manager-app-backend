from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


class CompleteTaskPostHandlingRequest(BaseModel):
    task_id: str | None = None
    post_handling_id: str | None = None
    force: bool = False


def parse_complete_task_post_handling_request(data: dict) -> CompleteTaskPostHandlingRequest:
    try:
        return CompleteTaskPostHandlingRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def complete_task_post_handling(ctx: ServiceContext) -> dict:
    request = parse_complete_task_post_handling_request(ctx.incoming_data)
    if request.post_handling_id is None and request.task_id is None:
        raise ValidationError("Either post_handling_id or task_id is required.")

    async with maybe_begin(ctx.session):
        if request.post_handling_id is not None:
            filters = [
                TaskPostHandling.workspace_id == ctx.workspace_id,
                TaskPostHandling.client_id == request.post_handling_id,
            ]
            if request.task_id:
                filters.append(TaskPostHandling.task_id == request.task_id)
            result = await ctx.session.execute(
                select(TaskPostHandling).where(*filters)
            )
            instance = result.scalar_one_or_none()
        else:
            result = await ctx.session.execute(
                select(TaskPostHandling).where(
                    TaskPostHandling.workspace_id == ctx.workspace_id,
                    TaskPostHandling.task_id == request.task_id,
                    TaskPostHandling.state != TaskPostHandlingStateEnum.COMPLETED,
                )
            )
            instance = result.scalar_one_or_none()

        if instance is None:
            raise NotFound("Active task post-handling instance not found.")
        if instance.state == TaskPostHandlingStateEnum.COMPLETED:
            raise ValidationError("Post-handling instance is already completed.")
        if not request.force and instance.state != TaskPostHandlingStateEnum.FILLED:
            raise ValidationError(
                "Post-handling instance must be in state 'filled' to complete. Use force=true to override."
            )

        old_state = instance.state
        now = datetime.now(timezone.utc)
        instance.state = TaskPostHandlingStateEnum.COMPLETED
        instance.updated_at = now

        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK_POST_HANDLING,
            entity_client_id=instance.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=f"Post-handling marked completed (from {old_state.value})",
            field_name="state",
            from_value={"state": old_state.value},
            to_value={"state": TaskPostHandlingStateEnum.COMPLETED.value},
            created_by_id=ctx.user_id,
            username_snapshot=ctx.identity.get("username"),
        )

    await event_bus.dispatch([
        build_workspace_event(instance, "task_post_handling:completed", workspace_id=ctx.workspace_id),
    ])
    return {"client_id": instance.client_id}
