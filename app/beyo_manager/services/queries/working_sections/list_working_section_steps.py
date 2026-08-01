from sqlalchemy import and_, case, distinct, exists, or_, select

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.state_filters import (
    parse_step_readiness_filter,
    parse_step_state_filter,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.upholstery_grouping import (
    build_primary_item_upholstery_group_columns,
)
from beyo_manager.services.queries.working_sections.steps_list_payload import (
    build_steps_list_payload,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def list_working_section_steps(ctx: ServiceContext) -> dict:
    working_section_id = ctx.incoming_data.get("working_section_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    task_types = _split_csv(ctx.query_params.get("task_types"))
    upholstery_search = str(ctx.query_params.get("upholstery_search", "false")).lower() == "true"
    group_by_upholstery = str(ctx.query_params.get("group_by_upholstery", "false")).lower() == "true"
    record_step_states = parse_step_state_filter(ctx.query_params.get("record_step_state"))
    readiness_statuses = parse_step_readiness_filter(ctx.query_params.get("readiness_statuses"))
    item_major_category_snapshot_raw = (
        ctx.query_params.get("item_major_category")
        or ctx.query_params.get("major_category")
    )
    item_major_category_snapshots = (
        list(dict.fromkeys([s.strip() for s in item_major_category_snapshot_raw.split(",") if s.strip()]))
        if item_major_category_snapshot_raw
        else []
    )
    item_position = ctx.query_params.get("item_position")
    item_zone = ctx.query_params.get("item_zone")

    ws_result = await ctx.session.execute(
        select(WorkingSection).where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id == working_section_id,
            WorkingSection.is_deleted.is_(False),
        )
    )
    if ws_result.scalar_one_or_none() is None:
        raise NotFound("Working section not found.")

    # Reassigned steps for the requesting user: any non-deleted acknowledgment
    # obligation on a non-terminal step in this section. These float to the top of
    # the list (within whatever the filters below allow) and are flagged per item.
    reassigned_result = await ctx.session.execute(
        select(TaskStepAcknowledgment.step_id)
        .join(TaskStep, TaskStep.client_id == TaskStepAcknowledgment.step_id)
        .where(
            TaskStepAcknowledgment.workspace_id == ctx.workspace_id,
            TaskStepAcknowledgment.worker_id == ctx.user_id,
            TaskStepAcknowledgment.is_deleted.is_(False),
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id == working_section_id,
            TaskStep.is_deleted.is_(False),
            TaskStep.state.notin_(TERMINAL_STEP_STATES),
        )
        .distinct()
    )
    reassigned_step_ids = {row[0] for row in reassigned_result.all()}

    # Prepend a "reassigned first" sort key when the viewer has any. Composes with
    # the record_step_state / readiness / search filters — it only reorders the
    # rows those filters allow through.
    # Grouping outranks the reassigned-first key: a reassigned step floating
    # above all groups would render under the wrong group header, so it only
    # floats to the top of its own upholstery group.
    upholstery_group_key = None
    upholstery_group_image_url = None
    upholstery_group_upholstery_id = None
    if group_by_upholstery:
        upholstery_group_key, upholstery_group_image_url, upholstery_group_upholstery_id = (
            build_primary_item_upholstery_group_columns(ctx.workspace_id, TaskStep.task_id)
        )

    order_by_clauses = []
    if upholstery_group_key is not None:
        order_by_clauses.append(upholstery_group_key.asc().nullslast())
    if reassigned_step_ids:
        order_by_clauses.append(
            case((TaskStep.client_id.in_(reassigned_step_ids), 0), else_=1)
        )
    order_by_clauses.extend([Task.ready_by_at.asc().nullslast(), TaskStep.client_id.desc()])

    stmt = (
        select(TaskStep.client_id)
        .join(Task, and_(Task.client_id == TaskStep.task_id, Task.is_deleted.is_(False)))
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id == working_section_id,
            TaskStep.is_deleted.is_(False),
        )
        .order_by(*order_by_clauses)
    )

    if record_step_states:
        stmt = stmt.where(TaskStep.state.in_(record_step_states))

    if readiness_statuses:
        stmt = stmt.where(TaskStep.readiness_status.in_(readiness_statuses))

    if task_types:
        stmt = stmt.where(Task.task_type.in_(task_types))

    if item_major_category_snapshots:
        stmt = stmt.where(
            exists(
                select(1)
                .select_from(TaskItem)
                .join(
                    Item,
                    and_(
                        Item.client_id == TaskItem.item_id,
                        Item.workspace_id == ctx.workspace_id,
                        Item.is_deleted.is_(False),
                    ),
                )
                .where(
                    TaskItem.task_id == TaskStep.task_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
                    Item.item_major_category_snapshot.in_(item_major_category_snapshots),
                )
            )
        )

    if item_position or item_zone:
        item_attr_conditions = []
        if item_position:
            item_attr_conditions.append(Item.item_position.ilike(item_position))
        if item_zone:
            item_attr_conditions.append(Item.item_zone.ilike(item_zone))
        stmt = stmt.where(
            exists(
                select(1)
                .select_from(TaskItem)
                .join(
                    Item,
                    and_(
                        Item.client_id == TaskItem.item_id,
                        Item.workspace_id == ctx.workspace_id,
                        Item.is_deleted.is_(False),
                    ),
                )
                .where(
                    TaskItem.task_id == TaskStep.task_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
                    *item_attr_conditions,
                )
            )
        )

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

    if upholstery_group_key is not None:
        stmt = stmt.add_columns(
            upholstery_group_key.label("upholstery_group_key"),
            upholstery_group_image_url.label("upholstery_group_image_url"),
            upholstery_group_upholstery_id.label("upholstery_group_upholstery_id"),
        )

    stmt = stmt.offset(offset).limit(limit + 1)

    ids_result = await ctx.session.execute(stmt)
    id_rows = ids_result.all()
    step_ids = [row[0] for row in id_rows]
    group_key_by_step_id = (
        {row[0]: row[1] for row in id_rows} if upholstery_group_key is not None else {}
    )
    group_image_by_step_id = (
        {row[0]: row[2] for row in id_rows} if upholstery_group_key is not None else {}
    )
    group_uph_id_by_step_id = (
        {row[0]: row[3] for row in id_rows} if upholstery_group_key is not None else {}
    )

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

    items_payload = await build_steps_list_payload(
        ctx,
        page_ids=page_ids,
        reassigned_step_ids=reassigned_step_ids,
        group_key_by_step_id=group_key_by_step_id,
        group_image_by_step_id=group_image_by_step_id,
        group_uph_id_by_step_id=group_uph_id_by_step_id,
    )

    return {
        "steps_pagination": {
            "items": items_payload,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
