"""Item cost summary by SKU for the external pricing app.

A deliberately flat read: purchase cost, expected sale price, restoration cost
and "other costs" (the cost-model terms this app subtracts from the sale price,
minus the purchase term).

Restoration cost is priced from the time recorded on the item's tasks, whether
or not a sale price was ever set: settled worked seconds × the task's committed
rate, else the current basis rate. Sections whose timing was marked inaccurate
count their typical time and are listed under `accuracy`. With no recorded time
it falls back to the committed production budget (`source: "planned"`). All
arithmetic is `calculator`'s; the typical is the production-time panel's.

Contract: `GET /api/v1/pricing/item-costs?sku=…` (routers/api_v1/pricing_api.py).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text

from beyo_manager.domain.item_economics.calculator import (
    calculate_actual_worker_minutes,
    calculate_consumed_cost_minor,
    calculate_term_amount,
)
from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.item_economics.typical_filters import project_typical_seconds
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.item_economics._common import _load_preview_inputs
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.pricing_api.auth import (
    refuse_pricing_api_auth,
    verify_pricing_api_request,
)
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import (
    typical_times_statement,
    unfiltered_evidence_from_row,
)

_ISO_CURRENCY = {
    ItemCurrencyEnum.SWEDISH_KRONA: "SEK",
    ItemCurrencyEnum.DANISH_KRONA: "DKK",
    ItemCurrencyEnum.EURO: "EUR",
}

RESTORATION_SOURCE_ACTUAL = "actual"
RESTORATION_SOURCE_PLANNED = "planned"


def _amount(minor: int) -> str:
    """Minor units → a two-decimal string. All three supported currencies have
    two minor digits."""
    return str((Decimal(minor) / Decimal(100)).quantize(Decimal("0.01")))


def _money(minor: int | None, updated_at: datetime | None, **extra) -> dict | None:
    if minor is None:
        return None
    return {
        "amount": _amount(minor),
        "updatedAt": updated_at.isoformat() if updated_at is not None else None,
        **extra,
    }


def _stamp(row) -> datetime:
    return getattr(row, "updated_at", None) or row.created_at


def _minutes(seconds: int) -> str:
    return str(calculate_actual_worker_minutes(seconds))


def _is_inaccurate(step: TaskStep) -> bool:
    return bool(step.recorded_time_marked_wrong) or (step.inaccurate_working_seconds or 0) > 0


async def _typical_seconds_by_section(
    ctx: ServiceContext, section_ids: set[str], quantity: int | None
) -> dict[str, int]:
    """The section typical the production-time panel uses (median of recent completed,
    accurately-timed work; null below the minimum sample), scaled to this item's
    quantity when a per-unit typical exists."""
    if not section_ids:
        return {}
    rows = await ctx.session.execute(
        typical_times_statement(ctx.workspace_id, now=ctx.now).where(
            WorkingSection.client_id.in_(section_ids)
        )
    )
    typicals: dict[str, int] = {}
    for row in rows:
        evidence = unfiltered_evidence_from_row(row)
        seconds = project_typical_seconds(evidence.section_typical_unit_worker_seconds, quantity)
        if seconds is None:
            seconds = evidence.section_typical_worker_seconds
        if seconds is not None:
            typicals[evidence.working_section_id] = seconds
    return typicals


async def _recorded_restoration(
    ctx: ServiceContext,
    item: Item,
    evaluations: list[ItemCostEvaluation],
    basis,
    currencies: dict[str, ItemCurrencyEnum],
) -> dict | None:
    """Restoration cost from the time recorded on the item's tasks.

    Tasks: every live task with this item as PRIMARY, plus any task holding one of
    its current committed evaluations. Seconds per task are the settled worked
    seconds of its live steps (what `process_item_cost_result` sums), except that
    a section whose timing was marked inaccurate counts its typical time instead
    — or, with no typical yet, its accurately-recorded remainder. Rate: the task's
    committed evaluation snapshot, else the current basis rate for the item's
    category. A task with no rate cannot be priced and is left out.

    Returns None when nothing priceable was recorded, so the caller can fall back
    to the committed budget.
    """
    evaluation_by_task = {row.task_id: row for row in evaluations}
    primary_task_ids = (
        await ctx.session.scalars(
            select(TaskItem.task_id).where(
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.item_id == item.client_id,
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
                TaskItem.removed_at.is_(None),
            )
        )
    ).all()
    task_ids = set(primary_task_ids) | set(evaluation_by_task)
    if not task_ids:
        return None
    tasks = {
        task.client_id: task
        for task in (
            await ctx.session.scalars(
                select(Task).where(
                    Task.workspace_id == ctx.workspace_id,
                    Task.client_id.in_(task_ids),
                    Task.is_deleted.is_(False),
                )
            )
        ).all()
    }
    steps = list(
        (
            await ctx.session.scalars(
                select(TaskStep)
                .where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id.in_(list(tasks)),
                    TaskStep.is_deleted.is_(False),
                )
                .order_by(TaskStep.task_id, TaskStep.sequence_order, TaskStep.client_id)
            )
        ).all()
    )
    groups: dict[tuple[str, str], list[TaskStep]] = {}
    for step in steps:
        groups.setdefault((step.task_id, step.working_section_id), []).append(step)
    flagged_sections = {
        section_id
        for (_task_id, section_id), group in groups.items()
        if any(_is_inaccurate(step) for step in group)
    }
    typicals = await _typical_seconds_by_section(ctx, flagged_sections, item.quantity)
    section_names: dict[str, str] = {}
    if flagged_sections:
        rows = await ctx.session.execute(
            select(WorkingSection.client_id, WorkingSection.name).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id.in_(flagged_sections),
            )
        )
        section_names = {str(row[0]): str(row[1]) for row in rows}

    total_cost = 0
    recorded_total = 0
    estimated_total = 0
    priced_any = False
    latest: datetime | None = None
    inaccurate_sections: list[dict] = []
    for task_id, task in tasks.items():
        evaluation = evaluation_by_task.get(task_id)
        if evaluation is not None:
            rate, currency = evaluation.cost_per_worker_minute_minor_snapshot, evaluation.currency
        elif basis is not None:
            rate, currency = basis.cost_per_worker_minute_minor, basis.currency
        else:
            continue
        recorded = 0
        estimated = 0
        task_flags: list[dict] = []
        for (group_task_id, section_id), group in groups.items():
            if group_task_id != task_id:
                continue
            accurate_seconds = sum(int(step.total_working_seconds or 0) for step in group)
            if not any(_is_inaccurate(step) for step in group):
                recorded += accurate_seconds
                continue
            typical = typicals.get(section_id)
            if typical is not None:
                estimated += typical
            else:
                recorded += accurate_seconds
            task_flags.append(
                {
                    "name": group[0].working_section_name_snapshot
                    or section_names.get(section_id)
                    or section_id,
                    "taskNumber": task.task_scalar_id,
                    "discardedMinutes": _minutes(
                        sum(int(step.inaccurate_working_seconds or 0) for step in group)
                    ),
                    "estimatedMinutes": _minutes(typical) if typical is not None else None,
                }
            )
        if recorded + estimated == 0 and not task_flags:
            continue
        priced_any = True
        currencies[f"task:{task_id}"] = currency
        total_cost += calculate_consumed_cost_minor(recorded + estimated, rate)
        recorded_total += recorded
        estimated_total += estimated
        inaccurate_sections.extend(task_flags)
        for step in steps:
            if step.task_id == task_id:
                stamp = _stamp(step)
                latest = stamp if latest is None or stamp > latest else latest

    if not priced_any or recorded_total + estimated_total == 0:
        return None
    return _money(
        total_cost,
        latest,
        source=RESTORATION_SOURCE_ACTUAL,
        accuracy={
            "isAccurate": not inaccurate_sections,
            "recordedMinutes": _minutes(recorded_total),
            "estimatedMinutes": _minutes(estimated_total),
            "inaccurateSections": inaccurate_sections,
        },
    )


async def get_item_costs_for_pricing_app(ctx: ServiceContext) -> dict:
    """Authenticate the pricing app, then answer for its configured workspace.

    `ctx.incoming_data` carries `headers` (the request headers) and `sku`. Auth
    runs here, inside `run_service`, so its refusal renders like any other
    `DomainError`.
    """
    workspace_id = verify_pricing_api_request(ctx.incoming_data["headers"])
    exists = (
        await ctx.session.execute(
            text("SELECT 1 FROM workspaces WHERE client_id = :ws"),
            {"ws": workspace_id},
        )
    ).first()
    if exists is None:
        raise refuse_pricing_api_auth("workspace_not_found")
    scoped = replace(
        ctx,
        identity={"workspace_id": workspace_id},
        incoming_data={"sku": ctx.incoming_data.get("sku")},
    )
    return await get_item_costs_by_sku(scoped)


async def _resolve_item(ctx: ServiceContext, sku: str) -> Item:
    """Exact SKU first; otherwise a case-insensitive match, but only if it is unique.

    SKUs are stored with mixed case ("Ch3-181126") while callers type them however
    they like. The unique index is case-sensitive, so two live items can differ
    only by case (production has one such pair) — that is refused as ambiguous
    rather than answered with a guess.
    """
    live = (Item.workspace_id == ctx.workspace_id, Item.is_deleted.is_(False))
    item = await ctx.session.scalar(select(Item).where(*live, Item.sku == sku))
    if item is not None:
        return item
    matches = list(
        (
            await ctx.session.scalars(
                select(Item).where(*live, func.lower(Item.sku) == sku.lower()).limit(2)
            )
        ).all()
    )
    if not matches:
        raise NotFound("Item not found.")
    if len(matches) > 1:
        raise ConflictError(
            "ITEM_SKU_AMBIGUOUS: more than one item matches this SKU when case is ignored; "
            "send the SKU with its exact case."
        )
    return matches[0]


async def get_item_costs_by_sku(ctx: ServiceContext) -> dict:
    sku = (ctx.incoming_data.get("sku") or "").strip()
    if not sku:
        raise NotFound("Item not found.")
    item = await _resolve_item(ctx, sku)

    currencies: dict[str, ItemCurrencyEnum] = {}

    # ── valuation: purchase cost + expected sale price ──────────────────────
    valuation = await ctx.session.scalar(
        select(ItemValuation).where(
            ItemValuation.workspace_id == ctx.workspace_id,
            ItemValuation.item_id == item.client_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    )
    purchase_cost = None
    expected_sale_price = None
    if valuation is not None:
        currencies["valuation"] = valuation.currency
        purchase_cost = _money(valuation.purchase_cost_minor, valuation.created_at)
        expected_sale_price = _money(valuation.expected_sale_price_minor, valuation.created_at)

    # Live configuration: the basis rate prices tasks that were never evaluated,
    # and the cost model prices "other costs".
    selection, terms = await _load_preview_inputs(ctx, item, now=ctx.now)

    # ── restoration: recorded time, else the committed budget ───────────────
    # Same "current committed evaluation" predicates as get_item_lifetime_economics.
    evaluations = list(
        (
            await ctx.session.scalars(
                select(ItemCostEvaluation)
                .where(
                    ItemCostEvaluation.workspace_id == ctx.workspace_id,
                    ItemCostEvaluation.item_id == item.client_id,
                    ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                    ItemCostEvaluation.superseded_at.is_(None),
                    ItemCostEvaluation.is_deleted.is_(False),
                )
                .order_by(
                    ItemCostEvaluation.committed_at.desc(),
                    ItemCostEvaluation.client_id.desc(),
                )
            )
        ).all()
    )
    restoration_cost = await _recorded_restoration(
        ctx, item, evaluations, selection.basis_version, currencies
    )
    if restoration_cost is None and evaluations:
        latest = evaluations[0]
        currencies[f"evaluation:{latest.task_id}"] = latest.currency
        restoration_cost = _money(
            latest.production_budget_minor,
            latest.committed_at,
            source=RESTORATION_SOURCE_PLANNED,
            accuracy=None,
        )

    # ── other costs: current cost-model terms, purchase term excluded ───────
    other_costs = None
    if valuation is not None and valuation.expected_sale_price_minor is not None:
        model = selection.cost_model_version
        if model is not None:
            currencies["cost_model"] = model.currency  # type: ignore[attr-defined]
            counted = [
                term
                for term in terms
                if term.calculation_type is not CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST
            ]
            total = sum(
                calculate_term_amount(
                    term.calculation_type,
                    valuation.expected_sale_price_minor,
                    term.percent_value,
                    term.fixed_amount_minor,
                    valuation.purchase_cost_minor,
                )
                for term in counted
            )
            other_costs = _money(
                total,
                max([valuation.created_at, _stamp(model), *(_stamp(term) for term in counted)]),
            )

    distinct = set(currencies.values())
    if len(distinct) > 1:
        detail = ", ".join(f"{source}={value.value}" for source, value in sorted(currencies.items()))
        raise ConflictError(f"ITEM_COST_CURRENCY_MISMATCH: {detail}")

    return {
        "sku": item.sku,
        "currency": _ISO_CURRENCY[distinct.pop()] if distinct else None,
        "expectedSalePrice": expected_sale_price,
        "purchaseCost": purchase_cost,
        "restorationCost": restoration_cost,
        "otherCosts": other_costs,
    }
