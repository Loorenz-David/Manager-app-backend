from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseStateEnum
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
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

_ACTIVE_STATES = [
    TaskStepStateEnum.WORKING,
    TaskStepStateEnum.PAUSED,
    TaskStepStateEnum.ENDED_SHIFT,
]

# 4-tier priority: open WORKING (0) > open PAUSED/ENDED_SHIFT (1) > closed WORKING (2) > closed PAUSED/ENDED_SHIFT (3)
_ACTIVE_RECORD_PRIORITY = case(
    (and_(StepStateRecord.state == TaskStepStateEnum.WORKING, StepStateRecord.exited_at.is_(None)), 0),
    (StepStateRecord.exited_at.is_(None), 1),
    (StepStateRecord.state == TaskStepStateEnum.WORKING, 2),
    else_=3,
)


async def _build_step_record_payload(ctx: ServiceContext, step: TaskStep) -> dict:
    """Assemble the full resume-card payload for a single step (task + item + images + cases + users).

    The step must be loaded with its `latest_state_record` relationship populated.
    """
    step_id = step.client_id
    task_id = step.task_id
    empty_case_summary = {"total_unread": 0}

    # Case summary for this task
    case_summary = empty_case_summary.copy()
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

    return {
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
        "cases_summary": case_summary,
    }


async def _load_step_with_latest_record(ctx: ServiceContext, step_id: str) -> TaskStep | None:
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


async def get_user_last_active_step_record(ctx: ServiceContext) -> dict:
    # 1. Find the step_id of the user's most relevant active record (the resume-card primary)
    step_id_result = await ctx.session.execute(
        select(StepStateRecord.step_id)
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .join(
            Task,
            and_(
                Task.client_id == TaskStep.task_id,
                Task.workspace_id == ctx.workspace_id,
                Task.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.created_by_id == ctx.user_id,
            StepStateRecord.state.in_(_ACTIVE_STATES),
        )
        .order_by(_ACTIVE_RECORD_PRIORITY.asc(), StepStateRecord.created_at.desc())
        .limit(1)
    )
    step_id = step_id_result.scalar_one_or_none()
    if step_id is None:
        return {"user_last_active_step_record": None, "active_batch_steps": None}

    # 2. Load the primary TaskStep with its latest state record
    primary_step = await _load_step_with_latest_record(ctx, step_id)
    if primary_step is None:
        return {"user_last_active_step_record": None, "active_batch_steps": None}

    primary_payload = await _build_step_record_payload(ctx, primary_step)

    # 3. If the primary step is batch-capable, surface the user's whole *open* active batch group.
    #    "Active batch group" = the user's batch steps that currently have an open active record
    #    (WORKING/PAUSED/ENDED_SHIFT, exited_at IS NULL). Non-batch primaries keep the single-step
    #    behavior untouched (active_batch_steps stays null).
    #    NOTE: this assembles per step; the active batch set is expected to be small (a worker's
    #    concurrently-open batch steps). If that set can grow large, batch-load the per-step data.
    active_batch_steps: list[dict] | None = None
    if primary_step.allows_batch_working:
        open_batch_rows = await ctx.session.execute(
            select(StepStateRecord.step_id)
            .join(
                TaskStep,
                and_(
                    TaskStep.client_id == StepStateRecord.step_id,
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.is_deleted.is_(False),
                    TaskStep.allows_batch_working.is_(True),
                ),
            )
            .join(
                Task,
                and_(
                    Task.client_id == TaskStep.task_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
            )
            .where(
                StepStateRecord.created_by_id == ctx.user_id,
                StepStateRecord.state.in_(_ACTIVE_STATES),
                StepStateRecord.exited_at.is_(None),
            )
            .order_by(StepStateRecord.entered_at.desc())
        )
        # Distinct, order-preserving (one open active record per step under the one-active invariant).
        ordered_step_ids: list[str] = []
        seen: set[str] = set()
        for (sid,) in open_batch_rows.all():
            if sid not in seen:
                seen.add(sid)
                ordered_step_ids.append(sid)

        if ordered_step_ids:
            payloads: list[dict] = []
            for sid in ordered_step_ids:
                if sid == primary_step.client_id:
                    payloads.append(primary_payload)
                    continue
                batch_step = await _load_step_with_latest_record(ctx, sid)
                if batch_step is not None:
                    payloads.append(await _build_step_record_payload(ctx, batch_step))
            active_batch_steps = payloads

    return {
        "user_last_active_step_record": primary_payload,
        "active_batch_steps": active_batch_steps,
    }
