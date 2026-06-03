from datetime import datetime, timezone

from sqlalchemy import func, select, text

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.customers.find_or_create_customer import find_or_create_customer
from beyo_manager.services.commands.items.batch_create_item_issues import _create_item_issues_in_session
from beyo_manager.services.commands.items.create_item_upholstery import _create_item_upholstery_in_session
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
from beyo_manager.services.commands.task_steps._wire_new_step_dependencies import (
    wire_batch_steps_into_dependency_graph,
)
from beyo_manager.services.commands.task_steps.assign_worker_to_step import (
    _assign_worker_to_step_in_session,
    _resolve_worker_for_section,
)
from beyo_manager.services.commands.tasks.create_task_note import _create_task_note_in_session
from beyo_manager.services.commands.tasks.requests import parse_create_task_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_create_message
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


_SELLER_ROLES = {"seller"}


async def create_task(ctx: ServiceContext) -> dict:
    request = parse_create_task_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        task_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            validate_provided_client_id(request.client_id, "tsk")
            existing_task = await ctx.session.get(Task, request.client_id)
            if existing_task is not None:
                raise ConflictError("Provided client_id is already in use.")
            task_kwargs["client_id"] = request.client_id

        await ctx.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:workspace_id))"),
            {"workspace_id": ctx.workspace_id},
        )
        scalar_id_result = await ctx.session.execute(
            select(func.coalesce(func.max(Task.task_scalar_id), 0) + 1).where(
                Task.workspace_id == ctx.workspace_id
            )
        )
        task_scalar_id = scalar_id_result.scalar_one()

        task_state = request.state or TaskStateEnum.PENDING
        if ctx.role_name in _SELLER_ROLES:
            task_state = TaskStateEnum.PENDING
        elif request.steps:
            task_state = TaskStateEnum.ASSIGNED

        task = Task(
            **task_kwargs,
            workspace_id=ctx.workspace_id,
            task_scalar_id=task_scalar_id,
            task_type=request.task_type,
            state=task_state,
            title=request.title,
            summary=request.summary,
            priority=request.priority,
            ready_by_at=request.ready_by_at,
            scheduled_start_at=request.scheduled_start_at,
            scheduled_end_at=request.scheduled_end_at,
            return_source=request.return_source,
            item_location=request.item_location,
            return_method=request.return_method,
            fulfillment_method=request.fulfillment_method,
            additional_details=request.additional_details,
            created_by_id=ctx.user_id,
        )

        if request.customer_id:
            task.customer_id = request.customer_id
            task.primary_phone_number = request.primary_phone_number
            task.secondary_phone_number = request.secondary_phone_number
            task.primary_email = request.primary_email
            task.secondary_email = request.secondary_email
            task.address = request.customer_address
        else:
            has_customer_payload = any(
                value is not None
                for value in [
                    request.customer_display_name,
                    request.primary_phone_number,
                    request.primary_email,
                    request.customer_address,
                ]
            )
            if has_customer_payload:
                customer_ctx = ServiceContext(
                    incoming_data={
                        "display_name": request.customer_display_name or "Unknown Customer",
                        "primary_email": request.primary_email,
                        "primary_phone_number": request.primary_phone_number,
                        "address": request.customer_address,
                    },
                    identity=ctx.identity,
                    session=ctx.session,
                )
                customer_result = await find_or_create_customer(customer_ctx)
                task.customer_id = customer_result["client_id"]

                customer_row = await ctx.session.execute(
                    select(Customer).where(
                        Customer.workspace_id == ctx.workspace_id,
                        Customer.client_id == task.customer_id,
                        Customer.is_deleted.is_(False),
                    )
                )
                customer = customer_row.scalar_one_or_none()
                if customer is None:
                    raise NotFound("Customer not found.")

                task.primary_phone_number = request.primary_phone_number or customer.primary_phone_number
                task.secondary_phone_number = request.secondary_phone_number
                task.primary_email = request.primary_email or customer.primary_email
                task.secondary_email = request.secondary_email
                task.address = request.customer_address or customer.address

        ctx.session.add(task)
        await ctx.session.flush()

        if request.notes:
            for note_input in request.notes:
                await _create_task_note_in_session(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    task_id=task.client_id,
                    note_type=note_input.note_type,
                    content=note_input.content,
                    user_id=ctx.user_id,
                    client_id=note_input.client_id,
                )

        item_id: str | None = None
        if request.item is not None:
            item_ctx = ServiceContext(
                incoming_data=request.item.model_dump(exclude_unset=True),
                identity=ctx.identity,
                session=ctx.session,
            )
            item_result = await find_or_create_item(item_ctx)
            item_id = item_result["client_id"]

            task_item = TaskItem(
                workspace_id=ctx.workspace_id,
                task_id=task.client_id,
                item_id=item_id,
                role=TaskItemRoleEnum.PRIMARY,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(task_item)
            await ctx.session.flush()

        if request.item_upholstery is not None:
            if item_id is None:
                raise ValidationError("item_upholstery requires item in payload.")
            if (
                request.item_upholstery.source == ItemUpholsterySourceEnum.INTERNAL
                and request.item_upholstery.upholstery_id is None
            ):
                raise ValidationError("upholstery_id is required when source is INTERNAL.")

            await _create_item_upholstery_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_id=item_id,
                upholstery_id=request.item_upholstery.upholstery_id,
                name=request.item_upholstery.name,
                code=request.item_upholstery.code,
                amount_meters=request.item_upholstery.amount_meters,
                source=request.item_upholstery.source,
                time_to_fix_in_seconds=request.item_upholstery.time_to_fix_in_seconds,
                user_id=ctx.user_id,
                client_id=request.item_upholstery.client_id,
            )

        if request.steps:
            now = datetime.now(timezone.utc)
            created_steps: list[TaskStep] = []
            for step_input in request.steps:
                if step_input.client_id is not None:
                    validate_provided_client_id(step_input.client_id, "tsp")
                    dup_step = await ctx.session.get(TaskStep, step_input.client_id)
                    if dup_step is not None:
                        raise ConflictError("Provided client_id for step is already in use.")

                section_result = await ctx.session.execute(
                    select(WorkingSection).where(
                        WorkingSection.workspace_id == ctx.workspace_id,
                        WorkingSection.client_id == step_input.working_section_id,
                        WorkingSection.is_deleted.is_(False),
                    )
                )
                section = section_result.scalar_one_or_none()
                if section is None:
                    raise NotFound(f"Working section {step_input.working_section_id!r} not found.")

                step = TaskStep(
                    **({"client_id": step_input.client_id} if step_input.client_id is not None else {}),
                    workspace_id=ctx.workspace_id,
                    task_id=task.client_id,
                    working_section_id=step_input.working_section_id,
                    working_section_name_snapshot=section.name,
                    state=TaskStepStateEnum.PENDING,
                    readiness_status=TaskStepReadinessStatusEnum.READY,
                    total_dependencies=0,
                    completed_dependencies=0,
                    sequence_order=step_input.sequence_order,
                    created_at=now,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(step)
                await ctx.session.flush()

                record = StepStateRecord(
                    workspace_id=ctx.workspace_id,
                    step_id=step.client_id,
                    state=TaskStepStateEnum.PENDING,
                    entered_at=now,
                    exited_at=None,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(record)
                await ctx.session.flush()

                step.latest_state_record_id = record.client_id
                created_steps.append(step)

                resolved_worker_id = await _resolve_worker_for_section(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    working_section_id=step_input.working_section_id,
                    explicit_worker_id=step_input.worker_id,
                )
                if resolved_worker_id is not None:
                    await _assign_worker_to_step_in_session(
                        session=ctx.session,
                        workspace_id=ctx.workspace_id,
                        step=step,
                        worker_id=resolved_worker_id,
                        user_id=ctx.user_id,
                        now=now,
                    )

            if created_steps:
                await wire_batch_steps_into_dependency_graph(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    new_steps=created_steps,
                    task_id=task.client_id,
                    user_id=ctx.user_id,
                )

        if request.item_issues:
            if item_id is None:
                raise ValidationError("item_issues require item in payload.")
            await _create_item_issues_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_id=item_id,
                issues_data=request.item_issues,
            )

        task.updated_at = datetime.now(timezone.utc)
        task.updated_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.CREATED,
            description=build_create_message(username, "task", "workspace"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        build_workspace_event(task, "task:created"),
    ])
    return {"client_id": task.client_id, "task_scalar_id": task.task_scalar_id}
