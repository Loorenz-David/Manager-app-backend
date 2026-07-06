from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


class CompleteTaskCustomerCoordinationRequest(BaseModel):
    task_id: str | None = None
    coordination_id: str | None = None


def parse_complete_task_customer_coordination_request(data: dict) -> CompleteTaskCustomerCoordinationRequest:
    try:
        return CompleteTaskCustomerCoordinationRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def complete_task_customer_coordination(ctx: ServiceContext) -> dict:
    request = parse_complete_task_customer_coordination_request(ctx.incoming_data)
    if request.coordination_id is None and request.task_id is None:
        raise ValidationError("Either coordination_id or task_id is required.")

    async with maybe_begin(ctx.session):
        if request.coordination_id is not None:
            filters = [
                TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                TaskCustomerCoordination.client_id == request.coordination_id,
            ]
            if request.task_id:
                filters.append(TaskCustomerCoordination.task_id == request.task_id)
            result = await ctx.session.execute(select(TaskCustomerCoordination).where(*filters))
            instance = result.scalar_one_or_none()
        else:
            result = await ctx.session.execute(
                select(TaskCustomerCoordination).where(
                    TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                    TaskCustomerCoordination.task_id == request.task_id,
                    TaskCustomerCoordination.state != TaskCustomerCoordinationStateEnum.COMPLETED,
                )
            )
            instance = result.scalar_one_or_none()

        if instance is None:
            raise NotFound("Active task customer coordination instance not found.")
        if instance.state == TaskCustomerCoordinationStateEnum.COMPLETED:
            raise ValidationError("Customer coordination instance is already completed.")

        old_state = instance.state
        now = datetime.now(timezone.utc)
        instance.state = TaskCustomerCoordinationStateEnum.COMPLETED
        instance.updated_at = now

        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
            entity_client_id=instance.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=f"Customer coordination marked completed (from {old_state.value})",
            field_name="state",
            from_value={"state": old_state.value},
            to_value={"state": TaskCustomerCoordinationStateEnum.COMPLETED.value},
            created_by_id=ctx.user_id,
            username_snapshot=ctx.identity.get("username"),
        )

    await event_bus.dispatch([
        build_workspace_event(instance, "task_customer_coordination:completed", workspace_id=ctx.workspace_id),
    ])
    return {"client_id": instance.client_id}
