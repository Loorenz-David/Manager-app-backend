from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import load_only

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.domain.items.location_push import needs_fixing_for_task_type
from beyo_manager.domain.items.upholstery_selection import should_defer_requirement_creation
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.sku_templates.events import SkuTemplateEvent
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.customers.find_or_create_customer import find_or_create_customer
from beyo_manager.services.commands.items._create_item_in_session import create_item_in_session
from beyo_manager.services.commands.items.batch_create_item_issues import _create_item_issues_in_session
from beyo_manager.services.commands.items.create_item_upholstery import _create_item_upholstery_in_session
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
from beyo_manager.services.commands.location_tracker.enqueue_item_zone_push import (
    enqueue_item_zone_location_push,
)
from beyo_manager.services.commands.shopify._create_preorder_sync_item_in_session import (
    _create_preorder_sync_item_in_session,
)
from beyo_manager.services.commands.sku_templates._allocate_sku_scalar_in_session import (
    allocate_sku_scalar_in_session,
)
from beyo_manager.services.commands.task_steps._wire_new_step_dependencies import (
    wire_batch_steps_into_dependency_graph,
)
from beyo_manager.services.commands.task_steps.assign_worker_to_step import (
    _assign_worker_to_step_in_session,
    _resolve_worker_for_section,
)
from beyo_manager.services.commands.tasks.note_writes import write_task_note
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
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent, WorkspaceEvent


_SELLER_ROLES = {"seller"}
_SHOPIFY_PREORDER_ROLES = {"admin", "manager", "seller"}


async def create_task(ctx: ServiceContext) -> dict:
    request = parse_create_task_request(ctx.incoming_data)
    if request.shopify_preorder is not None:
        if request.task_type != TaskTypeEnum.PRE_ORDER:
            raise ValidationError(
                "shopify_preorder is only valid for PRE_ORDER tasks."
            )
        if ctx.role_name not in _SHOPIFY_PREORDER_ROLES:
            raise PermissionDenied(
                "Your role cannot create Shopify pre-order products."
            )

    shopify_preorder_result: dict | None = None
    sku_events: list = []
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
            assortment=request.assortment,
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
                await write_task_note(
                    ctx,
                    task_id=task.client_id,
                    note_type=note_input.note_type,
                    content=note_input.content,
                    plain_text=note_input.plain_text,
                    users_read_list=note_input.users_read_list,
                    client_id=note_input.client_id,
                )

        item_id: str | None = None
        resolved_item: Item | None = None
        if request.item is not None:
            if request.item.article_number is None and request.item.sku is None:
                # Neither identifier was given, so the SKU template is this item's only
                # source of identity — there's nothing to look up an existing item by, so
                # this always creates fresh (never matches find_or_create_item's semantics).
                # Unlike the branch below, a missing template is a hard error here: with no
                # article_number and no template, the item would have no identity at all.
                item, item_events = await create_item_in_session(
                    ctx.session,
                    workspace_id=ctx.workspace_id,
                    user_id=ctx.user_id,
                    username=ctx.identity.get("username"),
                    client_id=request.item.client_id,
                    sku_template_task_type=request.task_type,
                    item_category_id=request.item.item_category_id,
                    quantity=request.item.quantity,
                    designer=request.item.designer,
                    height_in_cm=request.item.height_in_cm,
                    width_in_cm=request.item.width_in_cm,
                    depth_in_cm=request.item.depth_in_cm,
                    item_value_minor=request.item.item_value_minor,
                    item_cost_minor=request.item.item_cost_minor,
                    item_currency=request.item.item_currency,
                    item_position=request.item.item_position,
                    item_zone=request.item.item_zone,
                    external_id=request.item.external_id,
                    external_url=request.item.external_url,
                    external_source=request.item.external_source,
                    external_order_id=request.item.external_order_id,
                    can_have_upholstery=request.item.can_have_upholstery,
                    # This branch's TaskItem row does not exist yet, so a lookup would come
                    # back empty — the task being created is the one that decides.
                    needs_fixing=needs_fixing_for_task_type(request.task_type),
                )
                item_id = item.client_id
                resolved_item = item
                sku_events.extend(item_events)
            else:
                item_ctx = ServiceContext(
                    incoming_data=request.item.model_dump(exclude_unset=True),
                    identity=ctx.identity,
                    session=ctx.session,
                )
                deferred_pushes: list[Item] = []
                item_result = await find_or_create_item(
                    item_ctx, deferred_location_pushes=deferred_pushes
                )
                item_id = item_result["client_id"]
                resolved_item = await ctx.session.get(Item, item_id)
                if resolved_item is None:
                    raise NotFound("Item not found.")

                # Only backfill a SKU for an item find_or_create_item just created, and only
                # when the caller didn't supply one — never touch the sku of a pre-existing
                # item matched by article_number/sku. A task type with no configured template
                # (e.g. anything but PRE_ORDER today) silently leaves sku as None, same as
                # before this existed — this is an automatic helper, not a required field.
                if item_result["was_created"] and resolved_item.sku is None:
                    try:
                        resolved_sku, sku_template_id, reserved_scalar = await allocate_sku_scalar_in_session(
                            ctx.session,
                            workspace_id=ctx.workspace_id,
                            task_type=request.task_type,
                            user_id=ctx.user_id,
                        )
                    except NotFound:
                        resolved_sku = None
                    if resolved_sku is not None:
                        resolved_item.sku = resolved_sku
                        resolved_item.updated_by_id = ctx.user_id
                        sku_events.append(
                            WorkspaceEvent(
                                event_name=SkuTemplateEvent.SCALAR_RESERVED,
                                client_id=sku_template_id,
                                workspace_id=ctx.workspace_id,
                                extra={"last_scalar": reserved_scalar},
                            )
                        )

                # Deferred out of find_or_create_item so the outbound target snapshot includes
                # any sku backfilled just above — enqueueing inside that call would freeze a
                # payload carrying only the article_number for an item that ends up with both.
                # The create_item_in_session branch needs no equivalent: it resolves its sku
                # before building the row, so its own enqueue already sees the final values.
                for deferred_item in deferred_pushes:
                    await enqueue_item_zone_location_push(
                        ctx.session,
                        deferred_item,
                        username=ctx.identity.get("username"),
                        requested_by_user_id=ctx.user_id,
                        needs_fixing=needs_fixing_for_task_type(request.task_type),
                    )

            task_item = TaskItem(
                workspace_id=ctx.workspace_id,
                task_id=task.client_id,
                item_id=item_id,
                role=TaskItemRoleEnum.PRIMARY,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(task_item)
            await ctx.session.flush()

        if request.shopify_preorder is not None:
            shopify_preorder_result = await _create_preorder_sync_item_in_session(
                ctx,
                task_id=task.client_id,
                preorder=request.shopify_preorder,
                item_article_number=(
                    resolved_item.article_number if resolved_item is not None else None
                ),
                item_category_id=(
                    resolved_item.item_category_id if resolved_item is not None else None
                ),
                item_sku=resolved_item.sku if resolved_item is not None else None,
            )

        if request.item_upholstery is not None:
            if item_id is None:
                raise ValidationError("item_upholstery requires item in payload.")
            if (
                request.item_upholstery.source == ItemUpholsterySourceEnum.INTERNAL
                and request.item_upholstery.upholstery_id is None
                and not should_defer_requirement_creation(
                    request.item_upholstery.source,
                    request.item_upholstery.upholstery_id,
                    request.item_upholstery.amount_meters,
                )
            ):
                raise ValidationError(
                    "upholstery_id is required when source is INTERNAL unless positive amount_meters is provided."
                )

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

        created_steps: list[TaskStep] = []
        if request.steps:
            now = datetime.now(timezone.utc)

            section_ids = {s.working_section_id for s in request.steps}
            sections = (
                await ctx.session.execute(
                    select(WorkingSection)
                    .options(
                        load_only(
                            WorkingSection.client_id,
                            WorkingSection.name,
                            WorkingSection.allows_batch_working,
                        )
                    )
                    .where(
                        WorkingSection.workspace_id == ctx.workspace_id,
                        WorkingSection.client_id.in_(section_ids),
                        WorkingSection.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            section_map = {s.client_id: s for s in sections}
            missing_sections = sorted(section_ids - set(section_map))
            if missing_sections:
                raise NotFound(f"Working section {missing_sections[0]!r} not found.")

            provided_step_client_ids = [s.client_id for s in request.steps if s.client_id is not None]
            for cid in provided_step_client_ids:
                validate_provided_client_id(cid, "tsp")
            if provided_step_client_ids:
                existing_step_ids = (
                    await ctx.session.execute(
                        select(TaskStep.client_id).where(
                            TaskStep.workspace_id == ctx.workspace_id,
                            TaskStep.client_id.in_(provided_step_client_ids),
                        )
                    )
                ).scalars().all()
                if existing_step_ids:
                    raise ConflictError("Provided client_id for step is already in use.")

            for step_input in request.steps:
                section = section_map[step_input.working_section_id]

                step = TaskStep(
                    **({"client_id": step_input.client_id} if step_input.client_id is not None else {}),
                    workspace_id=ctx.workspace_id,
                    task_id=task.client_id,
                    working_section_id=step_input.working_section_id,
                    working_section_name_snapshot=section.name,
                    allows_batch_working=section.allows_batch_working,
                    state=TaskStepStateEnum.PENDING,
                    readiness_status=TaskStepReadinessStatusEnum.READY,
                    total_dependencies=0,
                    completed_dependencies=0,
                    sequence_order=step_input.sequence_order,
                    ready_by_at=(
                        step_input.ready_by_at
                        if step_input.ready_by_at is not None
                        else request.ready_by_at
                    ),
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

    pending_events: list = [
        build_workspace_event(
            task,
            "task:created",
            extra={"working_section_ids": [step.working_section_id for step in created_steps]},
        ),
        *sku_events,
    ]
    if created_steps:
        pending_events.append(
            BatchWorkspaceEvent(
                event_name="task:step-created",
                workspace_id=ctx.workspace_id,
                items=[
                    {
                        "client_id": step.client_id,
                        "working_section_id": step.working_section_id,
                    }
                    for step in created_steps
                ],
            )
        )
    await event_bus.dispatch(pending_events)
    result = {"client_id": task.client_id, "task_scalar_id": task.task_scalar_id}
    if resolved_item is not None:
        result["item_id"] = resolved_item.client_id
        result["item_sku"] = resolved_item.sku
    if shopify_preorder_result is not None:
        result["shopify_preorder"] = shopify_preorder_result
    return result
