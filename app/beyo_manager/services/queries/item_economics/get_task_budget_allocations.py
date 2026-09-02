"""Batched task budget allocations, derived from the current read model."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.item_economics import budget_division
from beyo_manager.domain.item_economics.budget_division import (
    ALLOCATION_METHOD,
    DivisionStep,
    divide_production_budget,
    _loaded_latest_state_record,
)
from beyo_manager.domain.item_economics.configuration import (
    resolve_economics_selection,
    resolve_item_economics_status,
    resolve_major_category,
)
from beyo_manager.domain.item_economics.division_serializers import serialize_budget_allocations
from beyo_manager.domain.item_economics.remaining_production_pressure import (
    PRESSURE_METHOD,
    compute_remaining_pressure,
)
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum, ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.typical_filters import (
    SectionTypicalEvidence,
    applied_projection_quantity,
    derive_spec_from_primary_item,
    project_typical_seconds,
    reconcile_task_typicals,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.live_worked_seconds import load_live_worked_seconds
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import (
    narrowed_evidence_from_row,
    section_evidence_from_row,
    typical_times_statement,
    unfiltered_evidence_from_row,
)
from beyo_manager.domain.item_economics.calculator import calculate_actual_worker_minutes, calculate_remaining_worker_minutes


_MAX_TASK_IDS = 50
_BUDGET_STATUSES = frozenset({EconomicsStatusEnum.OK, EconomicsStatusEnum.INFEASIBLE})


async def get_task_budget_allocations(ctx: ServiceContext) -> dict:
    task_ids = list(ctx.query_params.get("task_ids") or [])
    if len(task_ids) > _MAX_TASK_IDS:
        raise ValidationError(
            "BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS: at most 50 task ids may be requested"
        )

    tasks = (
        await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id.in_(task_ids),
                Task.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    visible_task_ids = [task.client_id for task in tasks]

    primary_rows = (
        await ctx.session.execute(
            select(TaskItem).where(
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.task_id.in_(visible_task_ids),
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
                TaskItem.removed_at.is_(None),
            )
        )
    ).scalars().all()
    primary_by_task = {row.task_id: row for row in primary_rows}
    item_ids = [row.item_id for row in primary_rows]
    items = (
        await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id.in_(item_ids),
                Item.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    item_by_id = {item.client_id: item for item in items}

    evaluations = (
        await ctx.session.execute(
            select(ItemCostEvaluation).where(
                ItemCostEvaluation.workspace_id == ctx.workspace_id,
                ItemCostEvaluation.task_id.in_(visible_task_ids),
                ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                ItemCostEvaluation.superseded_at.is_(None),
                ItemCostEvaluation.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    evaluation_by_task = {evaluation.task_id: evaluation for evaluation in evaluations}

    steps = (
        await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id.in_(visible_task_ids),
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    steps_by_task: dict[str, list[TaskStep]] = defaultdict(list)
    for step in steps:
        steps_by_task[step.task_id].append(step)

    live_seconds = await load_live_worked_seconds(
        ctx.session,
        ctx.workspace_id,
        steps,
        ctx.now,
    )
    selection_date = ctx.now.date()

    spec_by_task = {
        task.client_id: derive_spec_from_primary_item(
            item_by_id.get(primary_by_task[task.client_id].item_id)
            if task.client_id in primary_by_task
            else None
        )
        for task in tasks
    }
    # One statement for every task in the page: the specs are per task but the
    # categories behind them repeat heavily, and the names exist only so the
    # served `applied_filter` can say what the typicals were measured against.
    category_ids = {
        category_id
        for spec in spec_by_task.values()
        for category_id in (spec.item_category_ids or ())
    }
    category_names: dict[str, str] = {}
    if category_ids:
        category_names = {
            client_id: name
            for client_id, name in await ctx.session.execute(
                select(ItemCategory.client_id, ItemCategory.name).where(
                    ItemCategory.workspace_id == ctx.workspace_id,
                    ItemCategory.client_id.in_(category_ids),
                )
            )
        }

    narrowing_specs = []
    spec_index_by_task: dict[str, int | None] = {}
    for task in tasks:
        spec = spec_by_task[task.client_id]
        if not spec.is_narrowing:
            spec_index_by_task[task.client_id] = None
            continue
        if spec not in narrowing_specs:
            narrowing_specs.append(spec)
        spec_index_by_task[task.client_id] = narrowing_specs.index(spec)
    specs = tuple(narrowing_specs)
    typical_result = await ctx.session.execute(
        typical_times_statement(ctx.workspace_id, now=ctx.now, specs=specs)
    )
    typical_rows: dict[tuple[str, int | None], object] = {}
    for row in typical_result:
        index = int(row.spec_index) if specs else None
        typical_rows[(row.client_id, index)] = row

    # These four reads intentionally happen once per request. They mirror the
    # preview loader's query shapes and are resolved against each item in Python.
    groups = (
        await ctx.session.execute(
            select(ProductionCostGroup).where(
                ProductionCostGroup.workspace_id == ctx.workspace_id,
                ProductionCostGroup.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    basis_versions = (
        await ctx.session.execute(
            select(ProductionCostBasisVersion).where(
                ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
                ProductionCostBasisVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    cost_model_versions = (
        await ctx.session.execute(
            select(CostModelVersion).where(
                CostModelVersion.workspace_id == ctx.workspace_id,
                CostModelVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    terms = (
        await ctx.session.execute(
            select(CostModelTerm).where(
                CostModelTerm.workspace_id == ctx.workspace_id,
                CostModelTerm.is_deleted.is_(False),
            ).order_by(CostModelTerm.created_at.asc(), CostModelTerm.client_id.asc())
        )
    ).scalars().all()
    terms_by_model: dict[str, list[CostModelTerm]] = defaultdict(list)
    for term in terms:
        terms_by_model[term.cost_model_version_id].append(term)
    valuations = (
        await ctx.session.execute(
            select(ItemValuation).where(
                ItemValuation.workspace_id == ctx.workspace_id,
                ItemValuation.item_id.in_(item_ids),
                ItemValuation.superseded_at.is_(None),
                ItemValuation.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    valuation_by_item = {valuation.item_id: valuation for valuation in valuations}

    output = []
    for task in tasks:
        primary = primary_by_task.get(task.client_id)
        item = item_by_id.get(primary.item_id) if primary is not None else None
        evaluation = evaluation_by_task.get(task.client_id)
        if evaluation is None:
            if item is None:
                status = EconomicsStatusEnum.NOT_EVALUATED
            else:
                selection = resolve_economics_selection(
                    resolve_major_category(item.item_major_category_snapshot),
                    groups,
                    basis_versions,
                    cost_model_versions,
                    selection_date,
                )
                status = resolve_item_economics_status(
                    valuation_by_item.get(item.client_id),
                    selection,
                    terms_by_model.get(
                        selection.cost_model_version.client_id
                        if selection.cost_model_version is not None
                        else "",
                        [],
                    ),
                )
        else:
            status = EconomicsStatusEnum.INFEASIBLE if Decimal(evaluation.allowed_worker_minutes) <= 0 else EconomicsStatusEnum.OK

        task_steps = sorted(
            steps_by_task.get(task.client_id, []),
            key=lambda step: (step.sequence_order is None, step.sequence_order if step.sequence_order is not None else 0, step.client_id),
        )
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
            for step in task_steps
        ]
        section_ids = frozenset(step.working_section_id for step in task_steps)
        task_spec_index = spec_index_by_task[task.client_id]
        evidence_by_section: dict[str, SectionTypicalEvidence] = {}
        for section_id in section_ids:
            if specs and task_spec_index is None:
                row = typical_rows.get((section_id, 0))
                if row is None:
                    evidence_by_section[section_id] = SectionTypicalEvidence(section_id, None, 0, None, 0)
                else:
                    evidence_by_section[section_id] = section_evidence_from_row(section_id, row)
                continue
            row = typical_rows.get((section_id, task_spec_index if specs else None))
            if row is None:
                evidence_by_section[section_id] = SectionTypicalEvidence(section_id, None, 0, None, 0)
            elif specs:
                evidence_by_section[section_id] = narrowed_evidence_from_row(row)
            else:
                evidence_by_section[section_id] = unfiltered_evidence_from_row(row)
        selection = reconcile_task_typicals(
            evidence_by_section,
            spec_by_task[task.client_id] if spec_by_task[task.client_id].is_narrowing else None,
            frozenset(budget_division.participating_sections(division_steps)),
            section_ids,
        )
        allowed = evaluation.allowed_worker_minutes if evaluation is not None and status in _BUDGET_STATUSES else None
        division = divide_production_budget(allowed, division_steps, selection.selected)
        pressure = compute_remaining_pressure(division)
        item_quantity = item.quantity if item is not None else None
        projection_quantity = applied_projection_quantity(item_quantity)
        for step in division["steps"]:
            step["pressure_share_seconds"] = pressure.pressure_share_seconds_by_step_id[
                str(step["step_id"])
            ]
            selected = selection.selected.get(str(step["working_section_id"]))
            unit_seconds = selected.typical_unit_worker_seconds if selected is not None else None
            step["typical_unit_worker_seconds"] = unit_seconds
            step["projected_typical_worker_seconds"] = project_typical_seconds(
                unit_seconds, item_quantity
            )
        actual_seconds = sum(live_seconds[step.client_id] for step in task_steps)
        if status in _BUDGET_STATUSES and allowed is not None:
            actual_minutes = calculate_actual_worker_minutes(actual_seconds)
            remaining_minutes = calculate_remaining_worker_minutes(Decimal(allowed), actual_minutes)
            allowed_payload = Decimal(allowed)
        else:
            actual_seconds = None
            remaining_minutes = None
            allowed_payload = None

        output.append(
            {
                "task_id": task.client_id,
                "status": status.value,
                "allowed_worker_minutes": allowed_payload,
                "actual_worker_seconds": actual_seconds,
                "remaining_worker_minutes": remaining_minutes,
                "allocation_method": ALLOCATION_METHOD,
                "pressure_ratio": pressure.pressure_ratio,
                "pressure_method": PRESSURE_METHOD,
                "typical_resolution": selection,
                "item_category_names": category_names,
                "projection_quantity": projection_quantity,
                "steps": division["steps"],
            }
        )
    return serialize_budget_allocations(output)


__all__ = ["get_task_budget_allocations"]
