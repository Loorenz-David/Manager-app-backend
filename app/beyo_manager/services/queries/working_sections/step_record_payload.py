from sqlalchemy import and_, func, select
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
from beyo_manager.services.context import ServiceContext


async def build_step_record_payload(
    ctx: ServiceContext, step: TaskStep, *, include_cases_summary: bool = True
) -> dict:
    """Assemble the full resume-card payload for a single step.

    The step must be loaded with its ``latest_state_record`` relationship populated.

    ``cases_summary.total_unread`` is viewer-relative (counted against
    ``ctx.user_id``). Callers whose ``ctx.user_id`` is not the step's worker
    (e.g. a manager pulling another user's step) should pass
    ``include_cases_summary=False`` to omit the field rather than surface an
    unread count that reflects the caller instead of the worker.
    """
    step_id = step.client_id
    task_id = step.task_id

    # Case summary for this task (viewer-relative; only computed when requested)
    case_summary = {"total_unread": 0}
    if include_cases_summary:
        try:
            case_rows = await ctx.session.execute(
                select(
                    CaseConversation.last_message_seq.label("last_message_seq"),
                    CaseParticipant.last_read_message_seq.label("last_read_message_seq"),
                )
                .select_from(Case)
                .join(
                    CaseLink,
                    and_(
                        CaseLink.case_id == Case.client_id,
                        CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK,
                        CaseLink.entity_client_id == task_id,
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
            total_unread = 0
            for row in case_rows.all():
                if row.last_read_message_seq is not None:
                    total_unread += max((row.last_message_seq or 0) - row.last_read_message_seq, 0)
            case_summary = {"total_unread": total_unread}
        except Exception:
            pass

    # Task
    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    task = task_result.scalar_one_or_none()

    # Primary task item
    task_item_result = await ctx.session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id == task_id,
            TaskItem.removed_at.is_(None),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
        )
    )
    task_item = task_item_result.scalar_one_or_none()
    primary_item_id = task_item.item_id if task_item else None

    item: Item | None = None
    upholstery_by_id: dict[str, ItemUpholstery] = {}
    item_reqs: list[ItemUpholsteryRequirement] = []
    item_images: list = []

    if primary_item_id:
        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == primary_item_id,
                Item.is_deleted.is_(False),
            )
        )
        item = item_result.scalar_one_or_none()

        uph_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id == primary_item_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        upholsteries = uph_result.scalars().all()
        upholstery_by_id = {uph.client_id: uph for uph in upholsteries}

        upholstery_ids = list(upholstery_by_id.keys())
        if upholstery_ids:
            req_result = await ctx.session.execute(
                select(ItemUpholsteryRequirement).where(
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.item_upholstery_id.in_(upholstery_ids),
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                )
            )
            item_reqs = req_result.scalars().all()

        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                    ImageLink.entity_client_id == primary_item_id,
                ),
            )
            .options(
                selectinload(Image.last_event),
                selectinload(Image.image_annotations),
            )
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.display_order.asc())
        )
        for idx, (image, _) in enumerate(img_result.all()):
            if idx == 0:
                first_image = serialize_image(image, include_annotations=True)
                first_image.pop("image_annotations", None)
                item_images.append(first_image)
            else:
                item_images.append(serialize_image_light(image))

    # Users (creator, updater, state record author)
    user_ids = list({
        uid
        for uid in (
            step.created_by_id,
            step.updated_by_id,
            step.latest_state_record.created_by_id if step.latest_state_record else None,
        )
        if uid
    })
    users_map: dict[str, User] = {}
    if user_ids:
        users_result = await ctx.session.execute(
            select(User).where(User.client_id.in_(user_ids))
        )
        users_map = {user.client_id: user for user in users_result.scalars().all()}

    # first_started_at across all state records for this step
    first_started_result = await ctx.session.execute(
        select(func.min(StepStateRecord.entered_at)).where(StepStateRecord.step_id == step_id)
    )
    first_started_at = first_started_result.scalar_one_or_none()

    # Assemble full step payload (same shape as list_working_section_steps items)
    creator = users_map.get(step.created_by_id) if step.created_by_id else None
    updater = users_map.get(step.updated_by_id) if step.updated_by_id else None
    state_record_user = (
        users_map.get(step.latest_state_record.created_by_id)
        if step.latest_state_record and step.latest_state_record.created_by_id
        else None
    )

    payload = {
        **serialize_step(step),
        "updated_at": step.updated_at.isoformat() if step.updated_at else None,
        "created_by": serialize_user_working_section_member(creator) if creator else None,
        "updated_by": serialize_user_working_section_member(updater) if updater else None,
        "last_state_record": serialize_step_state_record_light(
            step.latest_state_record,
            user=state_record_user,
            first_started_at=first_started_at,
        ),
        "task": serialize_task_light(task) if task else None,
        "item": serialize_item_worker_light(item, item_reqs, upholstery_by_id),
        "item_images": item_images,
    }
    if include_cases_summary:
        payload["cases_summary"] = case_summary
    return payload


async def load_step_with_latest_record(ctx: ServiceContext, step_id: str) -> TaskStep | None:
    result = await ctx.session.execute(
        select(TaskStep)
        .join(
            Task,
            and_(
                Task.client_id == TaskStep.task_id,
                Task.workspace_id == ctx.workspace_id,
                Task.is_deleted.is_(False),
            ),
        )
        .options(selectinload(TaskStep.latest_state_record))
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.client_id == step_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()
