"""Query: paginated task flow records (history + step state records, merged and time-ordered)."""

from sqlalchemy import and_, or_, select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.history.enums import HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.serializers import serialize_history_flow_record, serialize_step_flow_record
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext

FLOW_RECORDS_LIMIT = 10


async def get_task_flow_records(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data["task_id"]
    offset = int(ctx.query_params.get("offset", 0))

    # 1. Verify task exists in this workspace.
    task_check = await ctx.session.execute(
        select(Task.client_id).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
        )
    )
    if task_check.scalar_one_or_none() is None:
        raise NotFound("Task not found.")

    # 2a. Collect item_ids from task_items (active only - removed_at IS NULL).
    item_result = await ctx.session.execute(
        select(TaskItem.item_id).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id == task_id,
            TaskItem.removed_at.is_(None),
        )
    )
    item_ids = [row[0] for row in item_result.all()]

    # 2b. Collect upholstery_ids from item_upholsteries.
    upholstery_ids: list[str] = []
    if item_ids:
        up_result = await ctx.session.execute(
            select(ItemUpholstery.client_id).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id.in_(item_ids),
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        upholstery_ids = [row[0] for row in up_result.all()]

    # 2c. Collect requirement_ids from item_upholstery_requirements.
    requirement_ids: list[str] = []
    if upholstery_ids:
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement.client_id).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id.in_(upholstery_ids),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        requirement_ids = [row[0] for row in req_result.all()]

    # 2d. Collect case_ids via CaseLink (CaseLink has no workspace_id - scoped implicitly via task_id).
    case_result = await ctx.session.execute(
        select(CaseLink.case_id).where(
            CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK,
            CaseLink.entity_client_id == task_id,
        )
    )
    case_ids = [row[0] for row in case_result.all()]

    # 2e. Collect step_ids from task_steps.
    step_id_result = await ctx.session.execute(
        select(TaskStep.client_id).where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.task_id == task_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    step_ids = [row[0] for row in step_id_result.all()]

    # 3. Fetch history records for all entity types in one join query.
    #    Always include the task entity type. Add other types only when their ID
    #    lists are non-empty to avoid empty IN() clauses.
    history_conditions = [
        and_(
            HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.TASK,
            HistoryRecordLink.entity_client_id == task_id,
        )
    ]
    if upholstery_ids:
        history_conditions.append(
            and_(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
                HistoryRecordLink.entity_client_id.in_(upholstery_ids),
            )
        )
    if requirement_ids:
        history_conditions.append(
            and_(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY_REQUIREMENT,
                HistoryRecordLink.entity_client_id.in_(requirement_ids),
            )
        )
    if case_ids:
        history_conditions.append(
            and_(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.CASE,
                HistoryRecordLink.entity_client_id.in_(case_ids),
            )
        )

    hist_result = await ctx.session.execute(
        select(HistoryRecord, HistoryRecordLink)
        .join(HistoryRecordLink, HistoryRecordLink.history_record_id == HistoryRecord.client_id)
        .where(or_(*history_conditions))
    )
    history_rows = hist_result.all()  # list[tuple[HistoryRecord, HistoryRecordLink]]

    # 4. Fetch step state records joined with task_steps for working_section_name_snapshot.
    step_state_rows: list = []
    if step_ids:
        ssr_result = await ctx.session.execute(
            select(StepStateRecord, TaskStep)
            .join(TaskStep, TaskStep.client_id == StepStateRecord.step_id)
            .where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.step_id.in_(step_ids),
                StepStateRecord.is_deleted.is_(False),
            )
        )
        step_state_rows = ssr_result.all()  # list[tuple[StepStateRecord, TaskStep]]

    # 5. Batch-load users for all created_by_ids in a single query.
    all_user_ids: set[str] = set()
    for record, _ in history_rows:
        if record.created_by_id:
            all_user_ids.add(record.created_by_id)
    for ssr, _ in step_state_rows:
        if ssr.created_by_id:
            all_user_ids.add(ssr.created_by_id)

    users_map: dict[str, User] = {}
    if all_user_ids:
        users_result = await ctx.session.execute(select(User).where(User.client_id.in_(all_user_ids)))
        users_map = {u.client_id: u for u in users_result.scalars().all()}

    # 6. Build a sortable raw list: (created_at_datetime, source_type, row_a, row_b).
    #    Sort before serializing to avoid string comparison on ISO timestamps.
    raw: list[tuple] = []
    for record, link in history_rows:
        raw.append((record.created_at, "history", record, link))
    for ssr, step in step_state_rows:
        raw.append((ssr.created_at, "step", ssr, step))

    raw.sort(key=lambda x: (x[0], x[2].client_id), reverse=True)

    # 7. Python-level offset pagination (limit + 1 trick for has_more).
    paged = raw[offset : offset + FLOW_RECORDS_LIMIT + 1]
    has_more = len(paged) > FLOW_RECORDS_LIMIT
    paged = paged[:FLOW_RECORDS_LIMIT]

    # 8. Serialize the page.
    flow_records = []
    for _, source_type, a, b in paged:
        if source_type == "history":
            flow_records.append(serialize_history_flow_record(a, b, users_map))
        else:
            flow_records.append(serialize_step_flow_record(a, b, users_map))

    return {
        "flow_records": flow_records,
        "flow_records_pagination": {
            "has_more": has_more,
            "limit": FLOW_RECORDS_LIMIT,
            "offset": offset,
        },
    }
