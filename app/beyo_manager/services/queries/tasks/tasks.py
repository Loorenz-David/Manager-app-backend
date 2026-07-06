from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.enums import TaskPriorityEnum
from beyo_manager.domain.tasks.serializers import (
    serialize_item,
    serialize_requirement,
    serialize_step,
    serialize_step_latest_state_record,
    serialize_task,
    serialize_upholstery,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.task_search import build_task_q_subquery

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _build_order_by(order_by: str | None):
    priority_rank = case(
        (Task.priority == TaskPriorityEnum.URGENT, 4),
        (Task.priority == TaskPriorityEnum.HIGH, 3),
        (Task.priority == TaskPriorityEnum.NORMAL, 2),
        (Task.priority == TaskPriorityEnum.LOW, 1),
        else_=0,
    )

    field_map = {
        "ready_by_at": Task.ready_by_at,
        "created_at": Task.created_at,
        "scheduled_start_at": Task.scheduled_start_at,
        "scheduled_end_at": Task.scheduled_end_at,
        "priority": priority_rank,
    }

    if not order_by:
        return [Task.ready_by_at.asc().nulls_last(), priority_rank.desc(), Task.created_at.asc()]

    order_clauses = []
    for part in [p.strip() for p in order_by.split(",") if p.strip()]:
        if ":" in part:
            field, direction = part.split(":", 1)
        else:
            field, direction = part, "asc"
        column = field_map.get(field)
        if column is None:
            continue
        if direction.lower() == "desc":
            order_clauses.append(column.desc())
        elif field == "ready_by_at":
            order_clauses.append(column.asc().nulls_last())
        else:
            order_clauses.append(column.asc())

    return order_clauses or [Task.ready_by_at.asc().nulls_last(), priority_rank.desc(), Task.created_at.asc()]


async def list_tasks(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    deleted = bool(ctx.query_params.get("deleted", False))

    working_section_ids = _split_csv(ctx.query_params.get("working_section_ids"))
    task_states = _split_csv(ctx.query_params.get("task_states"))
    task_step_states = _split_csv(ctx.query_params.get("task_step_states"))
    step_readiness_statuses = _split_csv(ctx.query_params.get("step_readiness_statuses"))
    priorities = _split_csv(ctx.query_params.get("priorities"))
    task_types = _split_csv(ctx.query_params.get("task_types"))
    return_sources = _split_csv(ctx.query_params.get("return_sources"))
    upholstery_requirement_states = _split_csv(ctx.query_params.get("upholstery_requirement_states"))
    post_handling_states = _split_csv(ctx.query_params.get("post_handling_states"))
    customer_coordination_states = _split_csv(ctx.query_params.get("customer_coordination_states"))

    ready_from_date = ctx.query_params.get("ready_from_date")
    ready_to_date = ctx.query_params.get("ready_to_date")
    scheduled_from_date = ctx.query_params.get("scheduled_from_date")
    scheduled_to_date = ctx.query_params.get("scheduled_to_date")

    stmt = select(Task.client_id).where(Task.workspace_id == ctx.workspace_id)
    stmt = stmt.where(Task.is_deleted.is_(True) if deleted else Task.is_deleted.is_(False))

    if task_states:
        stmt = stmt.where(Task.state.in_(task_states))
    if priorities:
        stmt = stmt.where(Task.priority.in_(priorities))
    if task_types:
        stmt = stmt.where(Task.task_type.in_(task_types))
    if return_sources:
        stmt = stmt.where(Task.return_source.in_(return_sources))

    if ready_from_date:
        stmt = stmt.where(Task.ready_by_at >= ready_from_date)
    if ready_to_date:
        stmt = stmt.where(Task.ready_by_at <= ready_to_date)
    if scheduled_from_date:
        stmt = stmt.where(Task.scheduled_start_at >= scheduled_from_date)
    if scheduled_to_date:
        stmt = stmt.where(Task.scheduled_end_at <= scheduled_to_date)

    if working_section_ids:
        section_subq = (
            select(TaskStep.task_id)
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
                TaskStep.working_section_id.in_(working_section_ids),
            )
            .distinct()
        )
        stmt = stmt.where(Task.client_id.in_(section_subq))

    if task_step_states:
        state_subq = (
            select(TaskStep.task_id)
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
                TaskStep.state.in_(task_step_states),
            )
            .distinct()
        )
        stmt = stmt.where(Task.client_id.in_(state_subq))

    if step_readiness_statuses:
        readiness_subq = (
            select(TaskStep.task_id)
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
                TaskStep.readiness_status.in_(step_readiness_statuses),
            )
            .distinct()
        )
        stmt = stmt.where(Task.client_id.in_(readiness_subq))

    if upholstery_requirement_states:
        req_subq = (
            select(TaskItem.task_id)
            .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
            .join(ItemUpholstery, and_(ItemUpholstery.item_id == Item.client_id, ItemUpholstery.is_deleted.is_(False)))
            .join(
                ItemUpholsteryRequirement,
                and_(
                    ItemUpholsteryRequirement.item_upholstery_id == ItemUpholstery.client_id,
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                ),
            )
            .where(
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.removed_at.is_(None),
                ItemUpholsteryRequirement.state.in_(upholstery_requirement_states),
            )
            .distinct()
        )
        stmt = stmt.where(Task.client_id.in_(req_subq))

    if post_handling_states:
        ph_subq = (
            select(TaskPostHandling.task_id)
            .where(
                TaskPostHandling.workspace_id == ctx.workspace_id,
                TaskPostHandling.state.in_(post_handling_states),
            )
            .distinct()
        )
        stmt = stmt.where(Task.client_id.in_(ph_subq))

    if customer_coordination_states:
        cc_subq = (
            select(TaskCustomerCoordination.task_id)
            .where(
                TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                TaskCustomerCoordination.state.in_(customer_coordination_states),
            )
            .distinct()
        )
        stmt = stmt.where(Task.client_id.in_(cc_subq))

    if q:
        stmt = stmt.where(Task.client_id.in_(build_task_q_subquery(ctx.workspace_id, q)))

    stmt = stmt.order_by(*_build_order_by(ctx.query_params.get("order_by")))
    stmt = stmt.offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    task_ids = [row[0] for row in result.all()]

    has_more = len(task_ids) > limit
    page_ids = task_ids[:limit]
    if not page_ids:
        return {
            "tasks_pagination": {
                "items": [],
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            }
        }

    tasks_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id.in_(page_ids),
        )
    )
    tasks = tasks_result.scalars().all()
    task_map = {task.client_id: task for task in tasks}

    post_handling_map: dict[str, list[TaskPostHandling]] = {}
    if post_handling_states:
        ph_result = await ctx.session.execute(
            select(TaskPostHandling)
            .where(
                TaskPostHandling.workspace_id == ctx.workspace_id,
                TaskPostHandling.task_id.in_(page_ids),
            )
            .order_by(TaskPostHandling.created_at.asc())
        )
        for ph in ph_result.scalars().all():
            post_handling_map.setdefault(ph.task_id, []).append(ph)

    customer_coordination_map: dict[str, list[TaskCustomerCoordination]] = {}
    if customer_coordination_states:
        cc_result = await ctx.session.execute(
            select(TaskCustomerCoordination)
            .where(
                TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                TaskCustomerCoordination.task_id.in_(page_ids),
            )
            .order_by(TaskCustomerCoordination.created_at.asc())
        )
        for cc in cc_result.scalars().all():
            customer_coordination_map.setdefault(cc.task_id, []).append(cc)

    task_items_result = await ctx.session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id.in_(page_ids),
            TaskItem.removed_at.is_(None),
        )
    )
    task_items = task_items_result.scalars().all()

    primary_item_ids = [ti.item_id for ti in task_items if ti.role.value == "primary"]
    items_map = {}
    if primary_item_ids:
        items_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id.in_(primary_item_ids),
                Item.is_deleted.is_(False),
            )
        )
        items_map = {item.client_id: item for item in items_result.scalars().all()}

    task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items if ti.role.value == "primary"}

    # Batch-load images for all primary items on this page in a single query.
    item_images_map: dict[str, list] = {}
    if primary_item_ids:
        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(ImageLink, and_(
                ImageLink.image_id == Image.client_id,
                ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                ImageLink.entity_client_id.in_(primary_item_ids),
            ))
            .options(selectinload(Image.last_event))
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, item_id in img_result.all():
            image_list = item_images_map.setdefault(item_id, [])
            image_list.append(serialize_image(image) if not image_list else serialize_image_light(image))

    items_payload = []
    for task_id in page_ids:
        task = task_map.get(task_id)
        if task is None:
            continue
        primary_item_id = task_to_primary_item_id.get(task_id)
        primary_item = items_map.get(primary_item_id)
        items_payload.append(
            {
                "task": serialize_task(
                    task,
                    post_handling_instances=post_handling_map.get(task_id) if post_handling_states else None,
                    customer_coordination_instances=(
                        customer_coordination_map.get(task_id) if customer_coordination_states else None
                    ),
                ),
                "primary_item": serialize_item(primary_item),
                "item_images": item_images_map.get(primary_item_id, []),
            }
        )

    return {
        "tasks_pagination": {
            "items": items_payload,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def list_task_counts(ctx: ServiceContext) -> dict:
    task_states = _split_csv(ctx.query_params.get("task_states"))
    task_step_states = _split_csv(ctx.query_params.get("task_step_states"))
    step_readiness_statuses = _split_csv(ctx.query_params.get("step_readiness_statuses"))
    priorities = _split_csv(ctx.query_params.get("priorities"))
    task_types = _split_csv(ctx.query_params.get("task_types"))
    return_sources = _split_csv(ctx.query_params.get("return_sources"))

    def _base_stmt():
        return (
            select(func.count(Task.client_id))
            .where(Task.workspace_id == ctx.workspace_id, Task.is_deleted.is_(False))
        )

    def _apply_step_state_filter(stmt, states):
        subq = (
            select(TaskStep.task_id)
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
                TaskStep.state.in_(states),
            )
            .distinct()
        )
        return stmt.where(Task.client_id.in_(subq))

    def _apply_readiness_filter(stmt, statuses):
        subq = (
            select(TaskStep.task_id)
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
                TaskStep.readiness_status.in_(statuses),
            )
            .distinct()
        )
        return stmt.where(Task.client_id.in_(subq))

    async def _count(stmt) -> int:
        result = await ctx.session.execute(stmt)
        return result.scalar_one() or 0

    # total — all active filters combined
    total_stmt = _base_stmt()
    if task_states:
        total_stmt = total_stmt.where(Task.state.in_(task_states))
    if priorities:
        total_stmt = total_stmt.where(Task.priority.in_(priorities))
    if task_types:
        total_stmt = total_stmt.where(Task.task_type.in_(task_types))
    if return_sources:
        total_stmt = total_stmt.where(Task.return_source.in_(return_sources))
    if task_step_states:
        total_stmt = _apply_step_state_filter(total_stmt, task_step_states)
    if step_readiness_statuses:
        total_stmt = _apply_readiness_filter(total_stmt, step_readiness_statuses)

    total = await _count(total_stmt)

    granularity: dict[str, dict[str, int]] = {}

    if task_states:
        counts = {}
        for state in task_states:
            stmt = _base_stmt().where(Task.state == state)
            if priorities:
                stmt = stmt.where(Task.priority.in_(priorities))
            if task_types:
                stmt = stmt.where(Task.task_type.in_(task_types))
            if return_sources:
                stmt = stmt.where(Task.return_source.in_(return_sources))
            if task_step_states:
                stmt = _apply_step_state_filter(stmt, task_step_states)
            if step_readiness_statuses:
                stmt = _apply_readiness_filter(stmt, step_readiness_statuses)
            counts[state] = await _count(stmt)
        granularity["task_states"] = counts

    if task_step_states:
        counts = {}
        for step_state in task_step_states:
            stmt = _base_stmt()
            if task_states:
                stmt = stmt.where(Task.state.in_(task_states))
            if priorities:
                stmt = stmt.where(Task.priority.in_(priorities))
            if task_types:
                stmt = stmt.where(Task.task_type.in_(task_types))
            if return_sources:
                stmt = stmt.where(Task.return_source.in_(return_sources))
            stmt = _apply_step_state_filter(stmt, [step_state])
            if step_readiness_statuses:
                stmt = _apply_readiness_filter(stmt, step_readiness_statuses)
            counts[step_state] = await _count(stmt)
        granularity["task_step_states"] = counts

    if step_readiness_statuses:
        counts = {}
        for readiness in step_readiness_statuses:
            stmt = _base_stmt()
            if task_states:
                stmt = stmt.where(Task.state.in_(task_states))
            if priorities:
                stmt = stmt.where(Task.priority.in_(priorities))
            if task_types:
                stmt = stmt.where(Task.task_type.in_(task_types))
            if return_sources:
                stmt = stmt.where(Task.return_source.in_(return_sources))
            if task_step_states:
                stmt = _apply_step_state_filter(stmt, task_step_states)
            stmt = _apply_readiness_filter(stmt, [readiness])
            counts[readiness] = await _count(stmt)
        granularity["step_readiness_statuses"] = counts

    if priorities:
        counts = {}
        for priority in priorities:
            stmt = _base_stmt().where(Task.priority == priority)
            if task_states:
                stmt = stmt.where(Task.state.in_(task_states))
            if task_types:
                stmt = stmt.where(Task.task_type.in_(task_types))
            if return_sources:
                stmt = stmt.where(Task.return_source.in_(return_sources))
            if task_step_states:
                stmt = _apply_step_state_filter(stmt, task_step_states)
            if step_readiness_statuses:
                stmt = _apply_readiness_filter(stmt, step_readiness_statuses)
            counts[priority] = await _count(stmt)
        granularity["priorities"] = counts

    if task_types:
        counts = {}
        for task_type in task_types:
            stmt = _base_stmt().where(Task.task_type == task_type)
            if task_states:
                stmt = stmt.where(Task.state.in_(task_states))
            if priorities:
                stmt = stmt.where(Task.priority.in_(priorities))
            if return_sources:
                stmt = stmt.where(Task.return_source.in_(return_sources))
            if task_step_states:
                stmt = _apply_step_state_filter(stmt, task_step_states)
            if step_readiness_statuses:
                stmt = _apply_readiness_filter(stmt, step_readiness_statuses)
            counts[task_type] = await _count(stmt)
        granularity["task_types"] = counts

    if return_sources:
        counts = {}
        for source in return_sources:
            stmt = _base_stmt().where(Task.return_source == source)
            if task_states:
                stmt = stmt.where(Task.state.in_(task_states))
            if priorities:
                stmt = stmt.where(Task.priority.in_(priorities))
            if task_types:
                stmt = stmt.where(Task.task_type.in_(task_types))
            if task_step_states:
                stmt = _apply_step_state_filter(stmt, task_step_states)
            if step_readiness_statuses:
                stmt = _apply_readiness_filter(stmt, step_readiness_statuses)
            counts[source] = await _count(stmt)
        granularity["return_sources"] = counts

    return {"total": total, "granularity": granularity}


async def get_task(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")
    include_deleted = bool(ctx.query_params.get("include_deleted", False))

    result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == client_id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None or (task.is_deleted and not include_deleted):
        raise NotFound("Task not found.")

    task_items_result = await ctx.session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id == task.client_id,
            TaskItem.removed_at.is_(None),
        )
    )
    task_items = task_items_result.scalars().all()

    primary_task_item = next((ti for ti in task_items if ti.role.value == "primary"), None)

    item = None
    if primary_task_item is not None:
        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == primary_task_item.item_id,
                Item.is_deleted.is_(False),
            )
        )
        item = item_result.scalar_one_or_none()

    item_images = []
    if item is not None:
        img_result = await ctx.session.execute(
            select(Image)
            .join(ImageLink, and_(
                ImageLink.image_id == Image.client_id,
                ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                ImageLink.entity_client_id == item.client_id,
            ))
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.display_order.asc())
        )
        item_images = img_result.scalars().all()

    upholsteries: list[ItemUpholstery] = []
    requirements: list[ItemUpholsteryRequirement] = []
    if item is not None:
        upholsteries_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id == item.client_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        upholsteries = upholsteries_result.scalars().all()

        if upholsteries:
            upholstery_ids = [u.client_id for u in upholsteries]
            requirements_result = await ctx.session.execute(
                select(ItemUpholsteryRequirement).where(
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.item_upholstery_id.in_(upholstery_ids),
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                )
            )
            requirements = requirements_result.scalars().all()

    steps_result = await ctx.session.execute(
        select(TaskStep)
        .options(selectinload(TaskStep.latest_state_record))
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.task_id == task.client_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    steps = steps_result.scalars().all()

    post_handling_result = await ctx.session.execute(
        select(TaskPostHandling)
        .where(
            TaskPostHandling.workspace_id == ctx.workspace_id,
            TaskPostHandling.task_id == task.client_id,
        )
        .order_by(TaskPostHandling.created_at.asc())
    )
    post_handling_instances = post_handling_result.scalars().all()

    unread_result = await ctx.session.execute(
        select(func.sum(
            case(
                (CaseConversation.last_message_seq > CaseParticipant.last_read_message_seq,
                 CaseConversation.last_message_seq - CaseParticipant.last_read_message_seq),
                else_=0,
            )
        ))
        .select_from(CaseLink)
        .join(CaseConversation, CaseConversation.case_id == CaseLink.case_id)
        .join(CaseParticipant, and_(
            CaseParticipant.case_id == CaseLink.case_id,
            CaseParticipant.user_id == ctx.user_id,
        ))
        .where(
            CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK,
            CaseLink.entity_client_id == task.client_id,
        )
    )
    unread_message_count = unread_result.scalar_one() or 0

    return {
        "task": serialize_task(task, post_handling_instances=list(post_handling_instances)),
        "item": serialize_item(item),
        "item_images": [serialize_image_light(img) for img in item_images],
        "item_upholstery": [serialize_upholstery(u) for u in upholsteries],
        "requirements": [serialize_requirement(r) for r in requirements],
        "task_steps": [
            {
                **serialize_step(step),
                "latest_state_records": serialize_step_latest_state_record(step.latest_state_record),
            }
            for step in steps
        ],
        "unread_message_count": unread_message_count,
    }
