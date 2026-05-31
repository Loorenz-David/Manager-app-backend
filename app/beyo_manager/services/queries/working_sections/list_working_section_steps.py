from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseStateEnum
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.domain.tasks.serializers import (
    serialize_item_worker_light,
    serialize_step,
    serialize_step_state_record_light,
    serialize_task_light,
)
from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_working_section_steps(ctx: ServiceContext) -> dict:
    working_section_id = ctx.incoming_data.get("working_section_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    upholstery_search = str(ctx.query_params.get("upholstery_search", "false")).lower() == "true"
    record_step_state_raw = ctx.query_params.get("record_step_state")
    record_step_states = [s.strip() for s in record_step_state_raw.split(",") if s.strip()] if record_step_state_raw else []

    ws_result = await ctx.session.execute(
        select(WorkingSection).where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id == working_section_id,
            WorkingSection.is_deleted.is_(False),
        )
    )
    if ws_result.scalar_one_or_none() is None:
        raise NotFound("Working section not found.")

    stmt = (
        select(TaskStep.client_id)
        .join(Task, and_(Task.client_id == TaskStep.task_id, Task.is_deleted.is_(False)))
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id == working_section_id,
            TaskStep.is_deleted.is_(False),
        )
        .order_by(Task.ready_by_at.asc().nullslast(), TaskStep.client_id.desc())
    )

    if record_step_states:
        stmt = stmt.where(TaskStep.state.in_(record_step_states))

    if q:
        q_like = f"%{q}%"

        q_stmt = (
            select(distinct(TaskStep.client_id))
            .select_from(TaskStep)
            .join(
                Task,
                and_(
                    Task.client_id == TaskStep.task_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
            )
            .join(
                TaskItem,
                and_(
                    TaskItem.task_id == Task.client_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
                ),
                isouter=True,
            )
            .join(
                Item,
                and_(
                    Item.client_id == TaskItem.item_id,
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                ),
                isouter=True,
            )
        )

        or_clauses = [
            Item.article_number.ilike(q_like),
            Item.sku.ilike(q_like),
        ]

        if upholstery_search:
            q_stmt = q_stmt.join(
                ItemUpholstery,
                and_(
                    ItemUpholstery.item_id == Item.client_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                ),
                isouter=True,
            )
            or_clauses.extend(
                [
                    ItemUpholstery.name.ilike(q_like),
                    ItemUpholstery.code.ilike(q_like),
                ]
            )

        q_stmt = q_stmt.where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id == working_section_id,
            TaskStep.is_deleted.is_(False),
            or_(*or_clauses),
        )

        stmt = stmt.where(TaskStep.client_id.in_(q_stmt))

    stmt = stmt.offset(offset).limit(limit + 1)

    ids_result = await ctx.session.execute(stmt)
    step_ids = [row[0] for row in ids_result.all()]

    has_more = len(step_ids) > limit
    page_ids = step_ids[:limit]

    if not page_ids:
        return {
            "steps_pagination": {
                "items": [],
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            }
        }

    steps_result = await ctx.session.execute(
        select(TaskStep)
        .options(selectinload(TaskStep.latest_state_record))
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.client_id.in_(page_ids),
        )
        .order_by(TaskStep.created_at.desc())
    )
    steps = steps_result.scalars().all()
    step_map = {step.client_id: step for step in steps}

    task_ids = list({step.task_id for step in steps})
    empty_case_summary = {
        "total_unread": 0,
    }

    case_summary_by_task: dict[str, dict] = {}
    if task_ids:
        try:
            case_summary_rows = await ctx.session.execute(
                select(
                    CaseLink.entity_client_id.label("task_id"),
                    CaseConversation.last_message_seq.label("last_message_seq"),
                    CaseParticipant.last_read_message_seq.label("last_read_message_seq"),
                )
                .select_from(Case)
                .join(
                    CaseLink,
                    and_(
                        CaseLink.case_id == Case.client_id,
                        CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK,
                        CaseLink.entity_client_id.in_(task_ids),
                    ),
                )
                .join(
                    Task,
                    and_(
                        Task.client_id == CaseLink.entity_client_id,
                        Task.workspace_id == ctx.workspace_id,
                        Task.is_deleted.is_(False),
                    ),
                )
                .join(CaseConversation, CaseConversation.case_id == Case.client_id)
                .outerjoin(
                    CaseParticipant,
                    and_(
                        CaseParticipant.case_id == Case.client_id,
                        CaseParticipant.user_id == ctx.user_id,
                    ),
                )
                .where(Case.state.in_([CaseStateEnum.OPEN, CaseStateEnum.RESOLVING]))
            )

            task_summary_buckets: dict[str, dict] = {}
            for row in case_summary_rows.all():
                bucket = task_summary_buckets.setdefault(row.task_id, empty_case_summary.copy())
                if row.last_read_message_seq is None:
                    continue
                bucket["total_unread"] += max((row.last_message_seq or 0) - row.last_read_message_seq, 0)

            case_summary_by_task = task_summary_buckets
        except Exception:
            case_summary_by_task = {}

    tasks_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id.in_(task_ids),
            Task.is_deleted.is_(False),
        )
    )
    task_map = {task.client_id: task for task in tasks_result.scalars().all()}

    task_items_result = await ctx.session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id.in_(task_ids),
            TaskItem.removed_at.is_(None),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
        )
    )
    task_items = task_items_result.scalars().all()
    task_to_primary_item_id = {task_item.task_id: task_item.item_id for task_item in task_items}

    primary_item_ids = list(task_to_primary_item_id.values())
    items_map: dict[str, Item] = {}
    if primary_item_ids:
        items_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id.in_(primary_item_ids),
                Item.is_deleted.is_(False),
            )
        )
        items_map = {item.client_id: item for item in items_result.scalars().all()}

    requirements_map: dict[str, list[ItemUpholsteryRequirement]] = {}
    upholstery_by_id: dict[str, ItemUpholstery] = {}
    if primary_item_ids:
        uph_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id.in_(primary_item_ids),
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        upholsteries = uph_result.scalars().all()
        upholstery_by_id = {upholstery.client_id: upholstery for upholstery in upholsteries}
        upholstery_id_to_item_id = {upholstery.client_id: upholstery.item_id for upholstery in upholsteries}

        upholstery_ids = list(upholstery_id_to_item_id.keys())
        if upholstery_ids:
            req_result = await ctx.session.execute(
                select(ItemUpholsteryRequirement).where(
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.item_upholstery_id.in_(upholstery_ids),
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                )
            )
            for requirement in req_result.scalars().all():
                item_id = upholstery_id_to_item_id.get(requirement.item_upholstery_id)
                if item_id is None:
                    continue
                requirements_map.setdefault(item_id, []).append(requirement)

    item_images_map: dict[str, list] = {}
    if primary_item_ids:
        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                    ImageLink.entity_client_id.in_(primary_item_ids),
                ),
            )
            .options(
                selectinload(Image.last_event),
                selectinload(Image.image_annotations),
            )
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, item_id in img_result.all():
            image_list = item_images_map.setdefault(item_id, [])
            if not image_list:
                # Keep the first image rich, including annotation details.
                first_image = serialize_image(image, include_annotations=True)
                first_image.pop("image_annotations", None)
                image_list.append(first_image)
            else:
                image_list.append(serialize_image_light(image))

    user_ids = list({
        user_id
        for step in steps
        for user_id in (
            step.created_by_id,
            step.updated_by_id,
            step.latest_state_record.created_by_id if step.latest_state_record else None,
        )
        if user_id
    })
    users_map: dict[str, User] = {}
    if user_ids:
        users_result = await ctx.session.execute(
            select(User).where(User.client_id.in_(user_ids))
        )
        users_map = {user.client_id: user for user in users_result.scalars().all()}

    first_started_result = await ctx.session.execute(
        select(
            StepStateRecord.step_id,
            func.min(StepStateRecord.entered_at).label("first_started_at"),
        )
        .where(StepStateRecord.step_id.in_(page_ids))
        .group_by(StepStateRecord.step_id)
    )
    first_started_map = {row.step_id: row.first_started_at for row in first_started_result.all()}

    items_payload = []
    for step_id in page_ids:
        step = step_map.get(step_id)
        if step is None:
            continue

        task = task_map.get(step.task_id)
        case_summary = case_summary_by_task.get(step.task_id, empty_case_summary.copy())
        primary_item_id = task_to_primary_item_id.get(step.task_id) if task else None
        item = items_map.get(primary_item_id) if primary_item_id else None
        creator = users_map.get(step.created_by_id) if step.created_by_id else None
        updater = users_map.get(step.updated_by_id) if step.updated_by_id else None
        item_reqs = requirements_map.get(primary_item_id, []) if primary_item_id else []
        state_record_user = (
            users_map.get(step.latest_state_record.created_by_id)
            if step.latest_state_record and step.latest_state_record.created_by_id
            else None
        )

        items_payload.append(
            {
                **serialize_step(step),
                "updated_at": step.updated_at.isoformat() if step.updated_at else None,
                "created_by": serialize_user_working_section_member(creator) if creator else None,
                "updated_by": serialize_user_working_section_member(updater) if updater else None,
                "last_state_record": serialize_step_state_record_light(
                    step.latest_state_record,
                    user=state_record_user,
                    first_started_at=first_started_map.get(step.client_id),
                ),
                "task": serialize_task_light(task) if task else None,
                "item": serialize_item_worker_light(item, item_reqs, upholstery_by_id),
                "item_images": item_images_map.get(primary_item_id, []) if primary_item_id else [],
                "cases_summary": case_summary,
            }
        )

    return {
        "steps_pagination": {
            "items": items_payload,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
