from datetime import datetime, timezone

from sqlalchemy import and_, func, select

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.working_sections.serializers import serialize_working_section_compact
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.services.context import ServiceContext

_ACTIVE_STATES = (
    TaskStepStateEnum.PENDING,
    TaskStepStateEnum.WORKING,
    TaskStepStateEnum.PAUSED,
    TaskStepStateEnum.ENDED_SHIFT,
    TaskStepStateEnum.BLOCKED,
)
_TERMINAL_STATES = (
    TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.SKIPPED,
    TaskStepStateEnum.FAILED,
)


async def get_worker_working_sections(ctx: ServiceContext) -> dict:
    today_start_raw = ctx.query_params.get("today_start")
    if today_start_raw:
        try:
            normalized = today_start_raw.replace("Z", "+00:00")
            today_start = datetime.fromisoformat(normalized)
            if today_start.tzinfo is None:
                today_start = today_start.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValidationError("today_start must be a valid ISO 8601 timestamp.") from exc
    else:
        now = datetime.now(tz=timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    membership_result = await ctx.session.execute(
        select(WorkingSectionMembership.working_section_id).where(
            WorkingSectionMembership.workspace_id == ctx.workspace_id,
            WorkingSectionMembership.user_id == ctx.user_id,
            WorkingSectionMembership.removed_at.is_(None),
        )
    )
    section_ids = [row[0] for row in membership_result.all()]

    if not section_ids:
        return {"working_sections": []}

    sections_result = await ctx.session.execute(
        select(WorkingSection)
        .where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id.in_(section_ids),
            WorkingSection.is_deleted.is_(False),
        )
        .order_by(WorkingSection.order_list.asc().nulls_last(), WorkingSection.name.asc())
    )
    sections = sections_result.scalars().all()
    active_section_ids = [s.client_id for s in sections]

    if not active_section_ids:
        return {"working_sections": []}

    active_counts_result = await ctx.session.execute(
        select(
            TaskStep.working_section_id,
            TaskStep.state,
            func.count().label("cnt"),
        )
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id.in_(active_section_ids),
            TaskStep.is_deleted.is_(False),
            TaskStep.state.in_(_ACTIVE_STATES),
        )
        .group_by(TaskStep.working_section_id, TaskStep.state)
    )

    terminal_counts_result = await ctx.session.execute(
        select(
            TaskStep.working_section_id,
            TaskStep.state,
            func.count().label("cnt"),
        )
        .join(
            StepStateRecord,
            and_(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.client_id == TaskStep.latest_state_record_id,
                StepStateRecord.entered_at >= today_start,
                StepStateRecord.is_deleted.is_(False),
            ),
        )
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id.in_(active_section_ids),
            TaskStep.is_deleted.is_(False),
            TaskStep.state.in_(_TERMINAL_STATES),
        )
        .group_by(TaskStep.working_section_id, TaskStep.state)
    )

    counts_map: dict[str, dict[str, int]] = {sid: {} for sid in active_section_ids}
    for row in active_counts_result.all():
        counts_map[row.working_section_id][row.state.value] = row.cnt
    for row in terminal_counts_result.all():
        counts_map[row.working_section_id][row.state.value] = row.cnt

    all_states = [state.value for state in (_ACTIVE_STATES + _TERMINAL_STATES)]

    return {
        "working_sections": [
            {
                **serialize_working_section_compact(
                    section.client_id,
                    section.name,
                    section.image,
                    section.order_list,
                ),
                "task_steps_counts": {
                    state: counts_map[section.client_id].get(state, 0)
                    for state in all_states
                },
            }
            for section in sections
        ]
    }
