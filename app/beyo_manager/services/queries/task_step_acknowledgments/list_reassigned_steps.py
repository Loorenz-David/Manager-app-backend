from sqlalchemy import and_, select

from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.domain.task_steps.serializers import serialize_task_step_acknowledgment
from beyo_manager.domain.working_sections.serializers import serialize_working_section_compact
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.task_step_acknowledgments._reassigned_steps_filters import (
    reassigned_steps_select_from,
    reassigned_steps_where_clauses,
)
from beyo_manager.services.queries.utils.string_filter import apply_string_filter
from beyo_manager.services.queries.working_sections.steps_list_payload import (
    build_steps_list_payload,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

_ALLOWED_STRING_COLUMNS = {
    "article_number": Item.article_number,
    "sku": Item.sku,
}


async def list_reassigned_steps(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    unacknowledged_only = str(ctx.query_params.get("unacknowledged_only", "false")).lower() == "true"
    q = ctx.query_params.get("q")
    string_filters = ctx.query_params.get("string_filters")

    stmt = reassigned_steps_select_from(select(TaskStepAcknowledgment), ctx)
    stmt = (
        stmt.join(
            TaskItem,
            and_(
                TaskItem.task_id == TaskStep.task_id,
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
                TaskItem.removed_at.is_(None),
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
        .where(*reassigned_steps_where_clauses(ctx, unacknowledged_only=unacknowledged_only))
    )
    stmt = apply_string_filter(stmt, q, string_filters, _ALLOWED_STRING_COLUMNS)
    stmt = stmt.order_by(
        TaskStepAcknowledgment.created_at.desc(),
        TaskStep.client_id.desc(),
    ).offset(offset).limit(limit + 1)

    rows = (await ctx.session.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    if not page:
        return {
            "steps_pagination": {"items": [], "limit": limit, "offset": offset, "has_more": has_more},
            "working_sections": {},
        }

    user_ids = {user_id for ack in page for user_id in (ack.worker_id, ack.created_by_id) if user_id}
    users_map: dict[str, User] = {}
    if user_ids:
        users_map = {
            user.client_id: user
            for user in (await ctx.session.execute(select(User).where(User.client_id.in_(user_ids)))).scalars().all()
        }

    page_ids = [ack.step_id for ack in page]
    items = await build_steps_list_payload(
        ctx,
        page_ids=page_ids,
        reassigned_step_ids=set(page_ids),
    )
    ack_by_step_id = {ack.step_id: ack for ack in page}
    for item in items:
        ack = ack_by_step_id[item["client_id"]]
        item["acknowledgment"] = serialize_task_step_acknowledgment(
            ack,
            worker=users_map.get(ack.worker_id),
            created_by=users_map.get(ack.created_by_id) if ack.created_by_id else None,
        )

    section_ids = {item["working_section_id"] for item in items}
    sections = (
        await ctx.session.execute(
            select(WorkingSection).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id.in_(section_ids),
                WorkingSection.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    working_sections = {
        section.client_id: serialize_working_section_compact(
            client_id=section.client_id,
            name=section.name,
            image=section.image,
            order_list=section.order_list,
            allows_batch_working=section.allows_batch_working,
            allows_shopify_product_modifications=section.allows_shopify_product_modifications,
        )
        for section in sections
    }
    return {
        "steps_pagination": {"items": items, "limit": limit, "offset": offset, "has_more": has_more},
        "working_sections": working_sections,
    }
