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


class FailTaskCustomerCoordinationRequest(BaseModel):
    task_id: str | None = None
    coordination_ids: list[str] | None = None


def parse_fail_task_customer_coordination_request(data: dict) -> FailTaskCustomerCoordinationRequest:
    try:
        return FailTaskCustomerCoordinationRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def fail_task_customer_coordination(ctx: ServiceContext) -> dict:
    request = parse_fail_task_customer_coordination_request(ctx.incoming_data)
    requested_ids = [coordination_id for coordination_id in (request.coordination_ids or []) if coordination_id]
    if request.task_id is None and not requested_ids:
        raise ValidationError("Either task_id or coordination_ids is required.")

    instances: list[TaskCustomerCoordination] = []

    async with maybe_begin(ctx.session):
        if requested_ids:
            filters = [
                TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                TaskCustomerCoordination.client_id.in_(requested_ids),
            ]
            if request.task_id:
                filters.append(TaskCustomerCoordination.task_id == request.task_id)

            result = await ctx.session.execute(select(TaskCustomerCoordination).where(*filters))
            instances_by_id = {instance.client_id: instance for instance in result.scalars().all()}
            instances = [
                instances_by_id[coordination_id]
                for coordination_id in requested_ids
                if coordination_id in instances_by_id
            ]
            if not instances:
                raise NotFound("Task customer coordination instances not found.")
        else:
            result = await ctx.session.execute(
                select(TaskCustomerCoordination).where(
                    TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                    TaskCustomerCoordination.task_id == request.task_id,
                    TaskCustomerCoordination.state.notin_(
                        [
                            TaskCustomerCoordinationStateEnum.COMPLETED,
                            TaskCustomerCoordinationStateEnum.FAILED,
                        ]
                    ),
                )
            )
            instance = result.scalar_one_or_none()
            if instance is None:
                raise NotFound("Active task customer coordination instance not found.")
            instances = [instance]

        now = datetime.now(timezone.utc)
        for instance in instances:
            if instance.state in (
                TaskCustomerCoordinationStateEnum.FAILED,
                TaskCustomerCoordinationStateEnum.COMPLETED,
            ):
                raise ValidationError(
                    f"Customer coordination {instance.client_id} is already {instance.state.value}."
                )

            old_state = instance.state
            instance.state = TaskCustomerCoordinationStateEnum.FAILED
            instance.updated_at = now

            await _create_history_record_in_session(
                session=ctx.session,
                entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
                entity_client_id=instance.client_id,
                change_type=HistoryRecordChangeTypeEnum.UPDATED,
                description=f"Customer coordination marked failed (from {old_state.value})",
                field_name="state",
                from_value={"state": old_state.value},
                to_value={"state": TaskCustomerCoordinationStateEnum.FAILED.value},
                created_by_id=ctx.user_id,
                username_snapshot=ctx.identity.get("username"),
            )

    await event_bus.dispatch(
        [
            build_workspace_event(instance, "task_customer_coordination:failed", workspace_id=ctx.workspace_id)
            for instance in instances
        ]
    )
    return {"failed_ids": [instance.client_id for instance in instances]}
