from sqlalchemy import and_, exists, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseStateEnum
from beyo_manager.domain.cases.serializers import serialize_case_list_item
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image_light
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_conversation_message import CaseConversationMessage
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter


_ALLOWED_STRING_COLUMNS = {
    "type_label": Case.type_label,
    "plain_text": CaseConversationMessage.plain_text,
    "item_article_number": Item.article_number,
    "item_sku": Item.sku,
}


def _parse_case_states(case_state: str) -> list[CaseStateEnum]:
    raw_values = [value.strip() for value in case_state.split(",") if value.strip()]
    if not raw_values:
        raise ValidationError("case_state must include at least one value")

    values: list[CaseStateEnum] = []
    invalid_values: list[str] = []
    for raw_value in raw_values:
        try:
            values.append(CaseStateEnum(raw_value))
        except ValueError:
            invalid_values.append(raw_value)

    if invalid_values:
        allowed = ", ".join(state.value for state in CaseStateEnum)
        invalid = ", ".join(invalid_values)
        raise ValidationError(f"Invalid case_state value(s): {invalid}. Allowed values: {allowed}")

    return values


async def list_cases(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    stmt = select(Case).options(
        selectinload(Case.conversations),
        selectinload(Case.links),
        selectinload(Case.created_by),
        selectinload(Case.case_type),
    )

    case_state = data.get("case_state")
    if case_state:
        stmt = stmt.where(Case.state.in_(_parse_case_states(case_state)))
    elif data.get("state"):
        try:
            stmt = stmt.where(Case.state == CaseStateEnum(data["state"]))
        except ValueError as exc:
            allowed = ", ".join(state.value for state in CaseStateEnum)
            raise ValidationError(f"Invalid state '{data['state']}'. Allowed values: {allowed}") from exc

    if data.get("created_by_id"):
        stmt = stmt.where(Case.created_by_id == data["created_by_id"])

    q = data.get("q")
    if q:
        stmt = (
            stmt
            .outerjoin(CaseConversation, CaseConversation.case_id == Case.client_id)
            .outerjoin(
                CaseConversationMessage,
                and_(
                    CaseConversationMessage.case_conversation_id == CaseConversation.client_id,
                    CaseConversationMessage.has_been_deleted.is_(False),
                ),
            )
            .outerjoin(
                CaseLink,
                and_(
                    CaseLink.case_id == Case.client_id,
                    CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK,
                ),
            )
            .outerjoin(
                Task,
                and_(
                    Task.client_id == CaseLink.entity_client_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
            )
            .outerjoin(
                TaskItem,
                and_(
                    TaskItem.task_id == Task.client_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                ),
            )
            .outerjoin(
                Item,
                and_(
                    Item.client_id == TaskItem.item_id,
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                ),
            )
        )
        stmt = apply_string_filter(stmt, q, None, _ALLOWED_STRING_COLUMNS)
        stmt = stmt.distinct(Case.client_id)

    if data.get("entity_type") and data.get("entity_client_id"):
        try:
            entity_type = CaseLinkEntityTypeEnum(data["entity_type"])
        except ValueError as exc:
            allowed = ", ".join(entity.value for entity in CaseLinkEntityTypeEnum)
            raise ValidationError(f"Invalid entity_type '{data['entity_type']}'. Allowed values: {allowed}") from exc

        stmt = stmt.where(
            exists(
                select(1).where(
                    CaseLink.case_id == Case.client_id,
                    CaseLink.entity_type == entity_type,
                    CaseLink.entity_client_id == data["entity_client_id"],
                )
            )
        )

    stmt = stmt.order_by(Case.created_at.desc()).offset(int(data.get("offset", 0))).limit(int(data.get("limit", 50)))
    cases = (await ctx.session.execute(stmt)).scalars().all()

    case_task_link: dict[str, str] = {}
    case_entity_type: dict[str, str | None] = {}
    for case in cases:
        links = getattr(case, "links", []) or []
        chosen = links[0] if links else None
        for link in links:
            if link.entity_type == CaseLinkEntityTypeEnum.TASK:
                chosen = link
                break
        case_entity_type[case.client_id] = chosen.entity_type.value if chosen else None
        if chosen and chosen.entity_type == CaseLinkEntityTypeEnum.TASK:
            case_task_link[case.client_id] = chosen.entity_client_id

    task_ids = list({task_id for task_id in case_task_link.values()})
    task_by_id: dict[str, Task] = {}
    if task_ids:
        tasks = (
            await ctx.session.execute(
                select(Task).where(
                    Task.client_id.in_(task_ids),
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        task_by_id = {task.client_id: task for task in tasks}

    task_items_by_task: dict[str, list[TaskItem]] = {}
    if task_by_id:
        task_items = (
            await ctx.session.execute(
                select(TaskItem).where(
                    TaskItem.task_id.in_(list(task_by_id.keys())),
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                )
            )
        ).scalars().all()
        for task_item in task_items:
            task_items_by_task.setdefault(task_item.task_id, []).append(task_item)

    task_primary_item_id: dict[str, str] = {}
    for task_id, items in task_items_by_task.items():
        ordered = sorted(items, key=lambda row: (row.role.value != "primary", row.created_at))
        task_primary_item_id[task_id] = ordered[0].item_id

    item_ids = list({item_id for item_id in task_primary_item_id.values()})
    item_by_id: dict[str, Item] = {}
    if item_ids:
        items = (
            await ctx.session.execute(
                select(Item).where(
                    Item.client_id.in_(item_ids),
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        item_by_id = {item.client_id: item for item in items}

    item_first_image: dict[str, dict] = {}
    if item_by_id:
        image_links = (
            await ctx.session.execute(
                select(ImageLink)
                .options(selectinload(ImageLink.image))
                .where(
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                    ImageLink.entity_client_id.in_(list(item_by_id.keys())),
                )
                .order_by(ImageLink.entity_client_id.asc(), ImageLink.display_order.asc(), ImageLink.created_at.asc())
            )
        ).scalars().all()
        for link in image_links:
            if link.entity_client_id not in item_first_image and link.image is not None:
                item_first_image[link.entity_client_id] = serialize_image_light(link.image)

    serialized_cases: list[dict] = []
    for case in cases:
        conversation = (getattr(case, "conversations", []) or [None])[0]
        task_id = case_task_link.get(case.client_id)
        task = task_by_id.get(task_id) if task_id else None
        item = None
        item_image = None
        if task is not None:
            item_id = task_primary_item_id.get(task.client_id)
            item = item_by_id.get(item_id) if item_id else None
            if item is not None:
                item_image = item_first_image.get(item.client_id)

        serialized_cases.append(
            serialize_case_list_item(
                case,
                case_type=case.__dict__.get("case_type"),
                created_by=getattr(case, "created_by", None),
                entity_type=case_entity_type.get(case.client_id),
                last_message_seq=conversation.last_message_seq if conversation is not None else 0,
                task=task,
                item=item,
                item_image=item_image,
            )
        )

    return {"cases": serialized_cases}
