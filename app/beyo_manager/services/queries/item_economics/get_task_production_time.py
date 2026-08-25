"""Task-scoped, section-keyed production-time read model."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.item_economics import budget_division
from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep,
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
    divide_production_budget,
    _loaded_latest_state_record,
)
from beyo_manager.domain.item_economics.division_serializers import serialize_task_production_time
from beyo_manager.domain.item_economics.remaining_production_pressure import (
    PRESSURE_METHOD,
    compute_remaining_pressure,
)
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.item_economics.typical_filters import (
    SectionTypicalEvidence,
    reconcile_task_typicals,
)
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.live_worked_seconds import load_live_worked_seconds
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import typical_times_statement


async def get_task_production_time(ctx: ServiceContext) -> dict:
    """Compose the manager budget status with the task's section view."""

    task_id = ctx.incoming_data.get("task_client_id")
    steps = (
        await ctx.session.execute(
            select(TaskStep)
            .options(selectinload(TaskStep.latest_state_record))
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == task_id,
                TaskStep.is_deleted.is_(False),
            )
            .order_by(TaskStep.client_id.asc())
        )
    ).scalars().all()
    live_seconds = await load_live_worked_seconds(
        ctx.session,
        ctx.workspace_id,
        steps,
        ctx.now,
    )
    status = await get_task_budget_status(ctx, live_seconds=live_seconds)
    division_steps = [
        DivisionStep(
            client_id=step.client_id,
            state=step.state,
            working_section_id=step.working_section_id,
            # Strict indexing is deliberate and fail-loud: a fallback would silently restore settled values and mask C3's population row.
            total_working_seconds=live_seconds[step.client_id],
            sequence_order=step.sequence_order,
            working_section_name_snapshot=step.working_section_name_snapshot,
            is_deleted=step.is_deleted,
            created_at=step.created_at,
            latest_state_record=_loaded_latest_state_record(step),
        )
        for step in steps
    ]
    section_ids = {step.working_section_id for step in steps}
    sections = (
        await ctx.session.execute(
            select(WorkingSection).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id.in_(section_ids),
                WorkingSection.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    section_by_id = {section.client_id: section for section in sections}

    spec = status.typical_filter_spec
    specs = (spec,) if spec is not None and spec.is_narrowing else ()
    evidence_by_section: dict[str, SectionTypicalEvidence] = {}
    if section_ids:
        typical_result = await ctx.session.execute(
            typical_times_statement(ctx.workspace_id, now=ctx.now, specs=specs).where(
                WorkingSection.client_id.in_(section_ids)
            )
        )
        for row in typical_result:
            if specs:
                # K >= 1 results are keyed by the named spec_index. Never rely
                # on the statement's column order; K2-a deliberately differs.
                if int(row.spec_index) != 0:
                    continue
                evidence_by_section[row.client_id] = SectionTypicalEvidence(
                    row.client_id,
                    int(row.narrowed_typical_worker_seconds) if row.narrowed_typical_worker_seconds is not None else None,
                    int(row.narrowed_sample_count or 0),
                    int(row.section_typical_worker_seconds) if row.section_typical_worker_seconds is not None else None,
                    int(row.section_sample_count or 0),
                )
            else:
                evidence_by_section[row.client_id] = SectionTypicalEvidence(
                    row.client_id,
                    None,
                    0,
                    int(row.typical_worker_seconds) if row.typical_worker_seconds is not None else None,
                    int(row.sample_count or 0),
                )
    section_ids = frozenset(section_ids)
    selection = reconcile_task_typicals(
        evidence_by_section,
        spec if specs else None,
        frozenset(budget_division.participating_sections(division_steps)),
        section_ids,
    )
    typicals_by_section = selection.selected
    typical_details = {
        section_id: {
            "typical_worker_seconds": selected.typical_worker_seconds,
            "typical_basis": selected.typical_basis,
            "sample_count": selected.sample_count,
            "narrowed_sample_count": selected.evidence.narrowed_sample_count,
            "section_sample_count": selected.evidence.section_sample_count,
            "method": TYPICAL_METHOD,
            "window_days": TYPICAL_WINDOW_DAYS,
            "min_sample_size": TYPICAL_MIN_SAMPLE_SIZE,
        }
        for section_id, selected in selection.selected.items()
    }

    division = divide_production_budget(
        status.allowed_worker_minutes
        if status.status in {EconomicsStatusEnum.OK, EconomicsStatusEnum.INFEASIBLE}
        else None,
        division_steps,
        typicals_by_section,
        section_by_id,
    )
    pressure = compute_remaining_pressure(division)
    pressure_by_section: dict[str, int | None] = {}
    open_pressure_by_section: dict[str, bool] = {}
    for step in division["steps"]:
        section_id = str(step["working_section_id"])
        state = str(step["state"])
        if state in {terminal.value for terminal in TERMINAL_STEP_STATES}:
            continue
        open_pressure_by_section[section_id] = True
        share = pressure.pressure_share_seconds_by_step_id[str(step["step_id"])]
        if share is not None:
            pressure_by_section[section_id] = pressure_by_section.get(section_id, 0) + share
    for section in division["sections"]:
        section_id = str(section["working_section_id"])
        section["pressure_share_seconds"] = (
            pressure_by_section.get(section_id, 0)
            if open_pressure_by_section.get(section_id)
            else None
        )
    return serialize_task_production_time(
        {
            "task_id": task_id,
            "status": status.status,
            "item_binding": status.item_binding,
            "allowed_worker_minutes": status.allowed_worker_minutes,
            "actual_worker_seconds": status.actual_worker_seconds,
            "actual_worker_minutes": status.actual_worker_minutes,
            "remaining_worker_minutes": status.remaining_worker_minutes,
            "percent_consumed": status.percent_consumed,
            "result": status.result,
            "division": division,
            "pressure_ratio": pressure.pressure_ratio,
            "pressure_method": PRESSURE_METHOD,
            "typicals": typical_details,
            "typical_resolution": selection,
        }
    )


__all__ = ["get_task_production_time"]
