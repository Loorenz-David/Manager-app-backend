from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.orm import aliased, selectinload

from beyo_manager.domain.emails.enums import EmailThreadEntityTypeEnum
from beyo_manager.domain.emails.serializers import serialize_email_message, serialize_email_thread
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.serializers import serialize_item, serialize_task
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.emails.email_thread_user_state import EmailThreadUserState
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.task_search import build_task_q_subquery

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def list_task_coordination_threads(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    coordination_states = _split_csv(ctx.query_params.get("coordination_states"))
    task_states = _split_csv(ctx.query_params.get("task_states"))
    task_types = _split_csv(ctx.query_params.get("task_types"))
    q = ctx.query_params.get("q")

    is_unread_sort = case(
        (
            EmailThread.last_inbound_message_at.is_not(None)
            & or_(
                EmailThreadUserState.last_read_at.is_(None),
                EmailThread.last_inbound_message_at > EmailThreadUserState.last_read_at,
            ),
            0,
        ),
        else_=1,
    )

    stmt = (
        select(EmailThread, TaskCustomerCoordination, Task, EmailThreadUserState)
        .join(
            TaskCustomerCoordination,
            TaskCustomerCoordination.client_id == EmailThread.entity_client_id,
        )
        .join(
            Task,
            and_(
                Task.client_id == TaskCustomerCoordination.task_id,
                Task.is_deleted.is_(False),
            ),
        )
        .join(
            EmailThreadUserState,
            and_(
                EmailThreadUserState.thread_id == EmailThread.client_id,
                EmailThreadUserState.user_id == ctx.user_id,
            ),
            isouter=True,
        )
        .where(
            EmailThread.workspace_id == ctx.workspace_id,
            EmailThread.entity_type == EmailThreadEntityTypeEnum.TASK_CUSTOMER_COORDINATION.value,
            TaskCustomerCoordination.workspace_id == ctx.workspace_id,
            Task.workspace_id == ctx.workspace_id,
        )
    )

    if coordination_states:
        stmt = stmt.where(TaskCustomerCoordination.state.in_(coordination_states))
    if task_states:
        stmt = stmt.where(Task.state.in_(task_states))
    if task_types:
        stmt = stmt.where(Task.task_type.in_(task_types))
    if q:
        q_like = f"%{q}%"
        email_q_subq = (
            select(distinct(EmailThread.client_id))
            .select_from(EmailThread)
            .join(
                EmailMessage,
                and_(
                    EmailMessage.thread_id == EmailThread.client_id,
                    EmailMessage.workspace_id == ctx.workspace_id,
                ),
                isouter=True,
            )
            .where(
                EmailThread.workspace_id == ctx.workspace_id,
                or_(
                    EmailThread.subject_normalized.ilike(q_like),
                    EmailThread.topic.ilike(q_like),
                    EmailMessage.subject.ilike(q_like),
                    EmailMessage.text_body_clean.ilike(q_like),
                    EmailMessage.body_preview.ilike(q_like),
                    EmailMessage.from_address.ilike(q_like),
                    EmailMessage.from_name.ilike(q_like),
                ),
            )
        )
        stmt = stmt.where(
            or_(
                Task.client_id.in_(build_task_q_subquery(ctx.workspace_id, q)),
                EmailThread.client_id.in_(email_q_subq),
            )
        )

    result = await ctx.session.execute(
        stmt.order_by(
            is_unread_sort.asc(),
            EmailThread.last_message_at.desc().nullslast(),
        )
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.all()

    has_more = len(rows) > limit
    page = rows[:limit]
    task_ids = [task.client_id for _, _, task, _ in page]
    thread_ids = [thread.client_id for thread, _, _, _ in page]

    task_items_result = await ctx.session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id.in_(task_ids),
            TaskItem.removed_at.is_(None),
        )
    )
    task_items = task_items_result.scalars().all()

    primary_item_ids = [ti.item_id for ti in task_items if ti.role.value == "primary"]
    task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items if ti.role.value == "primary"}

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
            .options(selectinload(Image.last_event))
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, item_id in img_result.all():
            image_list = item_images_map.setdefault(item_id, [])
            image_list.append(
                serialize_image(image) if not image_list else serialize_image_light(image)
            )

    last_messages_map: dict[str, list[EmailMessage]] = {}
    if thread_ids:
        ranked_messages = (
            select(
                EmailMessage,
                func.row_number()
                .over(
                    partition_by=EmailMessage.thread_id,
                    order_by=(
                        EmailMessage.sent_or_received_at.desc().nullslast(),
                        EmailMessage.created_at.desc(),
                    ),
                )
                .label("message_rank"),
            )
            .where(EmailMessage.thread_id.in_(thread_ids))
            .subquery()
        )
        ranked_email_message = aliased(EmailMessage, ranked_messages)
        msg_result = await ctx.session.execute(
            select(ranked_email_message)
            .where(ranked_messages.c.message_rank <= 2)
            .order_by(
                ranked_messages.c.thread_id,
                ranked_messages.c.message_rank.asc(),
            )
        )
        for msg in msg_result.scalars().all():
            last_messages_map.setdefault(msg.thread_id, []).append(msg)

    message_count_map: dict[str, int] = {}
    if thread_ids:
        count_result = await ctx.session.execute(
            select(EmailMessage.thread_id, func.count(EmailMessage.client_id))
            .where(EmailMessage.thread_id.in_(thread_ids))
            .group_by(EmailMessage.thread_id)
        )
        message_count_map = {thread_id: count for thread_id, count in count_result.all()}

    return {
        "coordination_threads": [
            {
                "thread": serialize_email_thread(thread, user_state),
                "task": serialize_task(task, customer_coordination_instances=[coordination]),
                "primary_item": serialize_item(items_map.get(task_to_primary_item_id.get(task.client_id))),
                "item_images": item_images_map.get(task_to_primary_item_id.get(task.client_id), []),
                "message_count": message_count_map.get(thread.client_id, 0),
                "last_messages": [
                    serialize_email_message(message)
                    for message in last_messages_map.get(thread.client_id, [])
                ],
                "last_message": (
                    serialize_email_message(last_messages_map[thread.client_id][0])
                    if last_messages_map.get(thread.client_id)
                    else None
                ),
            }
            for thread, coordination, task, user_state in page
        ],
        "coordination_threads_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
