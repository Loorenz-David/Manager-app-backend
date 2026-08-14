"""Commit the immutable item-cost decision and its task-scoped history."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.calculator import (
    CALCULATION_VERSION,
    calculate_allowed_worker_minutes,
    calculate_cost_per_worker_minute,
    calculate_production_budget,
    calculate_term_amounts,
)
from beyo_manager.domain.item_economics.configuration import (
    resolve_economics_selection,
    resolve_item_economics_status,
    resolve_major_category,
)
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum, ItemCostEvaluationKindEnum
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.item_economics._common import (
    _load_preview_inputs,
    audit,
    today_utc,
    translate_integrity_error,
    write_item_valuation_chain_in_session,
)
from beyo_manager.services.commands.item_economics.requests import (
    parse_commit_item_cost_evaluation_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


logger = logging.getLogger(__name__)
UNSET = object()
_ADMITTED_STATES = frozenset(
    {
        TaskStateEnum.PENDING,
        TaskStateEnum.ASSIGNED,
        TaskStateEnum.WORKING,
        TaskStateEnum.STALLED,
        TaskStateEnum.READY,
    }
)


def _figures(row: ItemCostEvaluation | None) -> dict | None:
    if row is None:
        return None
    return {
        "expected_sale_price_minor": row.expected_sale_price_minor,
        "purchase_cost_minor": row.purchase_cost_minor,
        "production_budget_minor": row.production_budget_minor,
        "allowed_worker_minutes": str(row.allowed_worker_minutes),
    }


def _status_error(status: EconomicsStatusEnum, item: Item, groups: list[ProductionCostGroup]) -> None:
    identities = {
        EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY: "ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY",
        EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP: "ITEM_COST_NO_COST_GROUP",
        EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP: "ITEM_COST_AMBIGUOUS_COST_GROUP",
        EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION: "ITEM_COST_NO_BASIS_VERSION",
        EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION: "ITEM_COST_NO_COST_MODEL_VERSION",
        EconomicsStatusEnum.ITEM_UNVALUED: "ITEM_COST_ITEM_UNVALUED",
        EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE: "ITEM_COST_EXPECTED_PRICE_REQUIRED",
        EconomicsStatusEnum.ITEM_MISSING_PURCHASE_COST: "ITEM_COST_PURCHASE_COST_REQUIRED",
        EconomicsStatusEnum.CURRENCY_MISMATCH: "ITEM_COST_CURRENCY_MISMATCH",
    }
    identity = identities[status]
    if status is EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY:
        detail = f"item {item.client_id} has no known major category"
    elif status is EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP:
        category = resolve_major_category(item.item_major_category_snapshot)
        matching = [group for group in groups if group.major_category == category]
        detail = f"{len(matching)} active cost groups for {category.value if category else 'unknown'}: {[g.client_id for g in matching]}"
    else:
        detail = status.value.replace("_", " ")
    raise ValidationError(f"{identity}: {detail}")


async def _load_task_and_primary(session, workspace_id: str, task_id: str) -> tuple[Task, TaskItem, Item]:
    task = await session.scalar(
        select(Task).where(
            Task.workspace_id == workspace_id,
            Task.client_id == task_id,
        ).with_for_update()
    )
    if task is None or task.is_deleted:
        raise NotFound("Task not found.")
    if task.state not in _ADMITTED_STATES:
        raise ValidationError(f"ITEM_COST_TASK_TERMINAL: task is {task.state.value}")

    primary = await session.scalar(
        select(TaskItem).where(
            TaskItem.workspace_id == workspace_id,
            TaskItem.task_id == task.client_id,
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            TaskItem.removed_at.is_(None),
        )
    )
    if primary is None:
        raise ValidationError("ITEM_COST_NO_PRIMARY_ITEM: task has no active PRIMARY item")
    item = await session.scalar(
        select(Item).where(
            Item.workspace_id == workspace_id,
            Item.client_id == primary.item_id,
            Item.is_deleted.is_(False),
        )
    )
    if item is None:
        raise NotFound("Item not found.")
    return task, primary, item


async def _load_live_inputs(session, workspace_id: str, item: Item):
    groups = list((await session.scalars(select(ProductionCostGroup).where(
        ProductionCostGroup.workspace_id == workspace_id,
        ProductionCostGroup.is_deleted.is_(False),
    ))).all())
    basis_versions = list((await session.scalars(
        select(ProductionCostBasisVersion).where(
            ProductionCostBasisVersion.workspace_id == workspace_id,
            ProductionCostBasisVersion.is_deleted.is_(False),
        ).with_for_update(read=True)
    )).all())
    model_versions = list((await session.scalars(
        select(CostModelVersion).where(
            CostModelVersion.workspace_id == workspace_id,
            CostModelVersion.is_deleted.is_(False),
        ).with_for_update(read=True)
    )).all())
    selection = resolve_economics_selection(
        resolve_major_category(item.item_major_category_snapshot),
        groups,
        basis_versions,
        model_versions,
        today_utc(),
    )
    terms = []
    if selection.cost_model_version is not None:
        terms = list((await session.scalars(
            select(CostModelTerm).where(
                CostModelTerm.workspace_id == workspace_id,
                CostModelTerm.cost_model_version_id == selection.cost_model_version.client_id,
                CostModelTerm.is_deleted.is_(False),
            ).order_by(CostModelTerm.created_at.asc(), CostModelTerm.client_id.asc())
        )).all())
    return groups, selection, terms


async def _load_current_valuation(session, workspace_id: str, item_id: str) -> ItemValuation | None:
    return await session.scalar(
        select(ItemValuation).where(
            ItemValuation.workspace_id == workspace_id,
            ItemValuation.item_id == item_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        ).with_for_update()
    )


async def _commit_item_cost_evaluation_in_session(
    session,
    *,
    workspace_id: str,
    task_id: str,
    user_id: str,
    expected_sale_price_minor=UNSET,
    purchase_cost_minor=UNSET,
    label: str | None = None,
    promoted_from_id: str | None = None,
    source_evaluation: ItemCostEvaluation | None = None,
    source_terms: list[CostModelTerm | ItemCostEvaluationTerm] | None = None,
    audit_event: str = "item_cost_evaluation.committed",
    kind: ItemCostEvaluationKindEnum = ItemCostEvaluationKindEnum.COMMITTED,
) -> tuple[ItemCostEvaluation, list]:
    """Run the nine-step procedure and gate committed-only effects by ``kind``.

    ``kind`` gates the chain S1 close scope, ``committed_at``, the valuation
    mirror, the history record, the audit row, and the pending event.
    """
    task, _primary, item = await _load_task_and_primary(session, workspace_id, task_id)
    if source_evaluation is None:
        groups, selection, live_terms = await _load_live_inputs(session, workspace_id, item)
        valuation = await _load_current_valuation(session, workspace_id, item.client_id)
        if valuation is None:
            effective = None
        else:
            effective = SimpleNamespace(
                expected_sale_price_minor=(
                    valuation.expected_sale_price_minor
                    if expected_sale_price_minor is UNSET
                    else expected_sale_price_minor
                ),
                purchase_cost_minor=(
                    valuation.purchase_cost_minor
                    if purchase_cost_minor is UNSET
                    else purchase_cost_minor
                ),
                currency=valuation.currency,
            )
        status = resolve_item_economics_status(effective, selection, live_terms)
        if status is not EconomicsStatusEnum.NOT_EVALUATED:
            _status_error(status, item, groups)
        assert selection.selected_group is not None
        assert selection.basis_version is not None
        assert selection.cost_model_version is not None
        basis = selection.basis_version
        model = selection.cost_model_version
        terms = live_terms
        expected_price = effective.expected_sale_price_minor
        purchase_cost = effective.purchase_cost_minor
        currency = valuation.currency
    else:
        valuation = await _load_current_valuation(session, workspace_id, item.client_id)
        terms = list(source_terms or [])
        basis = SimpleNamespace(
            client_id=source_evaluation.production_cost_basis_version_id,
            fixed_monthly_cost_minor=source_evaluation.fixed_monthly_cost_minor_snapshot,
            monthly_paid_hours_snapshot=source_evaluation.monthly_paid_hours_snapshot,
            monthly_paid_hours=source_evaluation.monthly_paid_hours_snapshot,
            planning_utilization_percent_snapshot=source_evaluation.planning_utilization_percent_snapshot,
            planning_utilization_percent=source_evaluation.planning_utilization_percent_snapshot,
        )
        model = SimpleNamespace(client_id=source_evaluation.cost_model_version_id)
        expected_price = source_evaluation.expected_sale_price_minor
        purchase_cost = source_evaluation.purchase_cost_minor
        currency = source_evaluation.currency
        if expected_sale_price_minor is not UNSET:
            expected_price = expected_sale_price_minor
        if purchase_cost_minor is not UNSET:
            purchase_cost = purchase_cost_minor
        if valuation is None:
            raise ValidationError("ITEM_COST_ITEM_UNVALUED: item has no current valuation")

    term_amounts = calculate_term_amounts(terms, expected_price, purchase_cost)
    rate = calculate_cost_per_worker_minute(
        basis.fixed_monthly_cost_minor,
        basis.monthly_paid_hours,
        basis.planning_utilization_percent,
    )
    budget = calculate_production_budget(expected_price, term_amounts)
    allowed = calculate_allowed_worker_minutes(budget, rate)
    now = datetime.now(timezone.utc)

    previous = None
    if kind is ItemCostEvaluationKindEnum.COMMITTED:
        previous = await session.scalar(
            select(ItemCostEvaluation).where(
                ItemCostEvaluation.workspace_id == workspace_id,
                ItemCostEvaluation.task_id == task.client_id,
                ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                ItemCostEvaluation.superseded_at.is_(None),
                ItemCostEvaluation.is_deleted.is_(False),
            )
        )
        await session.execute(
            update(ItemCostEvaluation)
            .where(
                ItemCostEvaluation.workspace_id == workspace_id,
                ItemCostEvaluation.task_id == task.client_id,
                ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                ItemCostEvaluation.superseded_at.is_(None),
                ItemCostEvaluation.is_deleted.is_(False),
            )
            .values(superseded_at=now)
        )

    evaluation = ItemCostEvaluation(
        workspace_id=workspace_id,
        task_id=task.client_id,
        item_id=item.client_id,
        kind=kind,
        label=label,
        task_type_snapshot=task.task_type,
        return_source_snapshot=task.return_source,
        expected_sale_price_minor=expected_price,
        purchase_cost_minor=purchase_cost,
        currency=currency,
        cost_model_version_id=model.client_id,
        production_cost_group_id=(
            source_evaluation.production_cost_group_id
            if source_evaluation is not None
            else selection.selected_group.client_id
        ),
        production_cost_basis_version_id=basis.client_id,
        monthly_paid_hours_snapshot=basis.monthly_paid_hours,
        planning_utilization_percent_snapshot=basis.planning_utilization_percent,
        fixed_monthly_cost_minor_snapshot=basis.fixed_monthly_cost_minor,
        cost_per_worker_minute_minor_snapshot=rate,
        production_budget_minor=budget,
        allowed_worker_minutes=allowed,
        calculation_version=CALCULATION_VERSION,
        committed_at=now if kind is ItemCostEvaluationKindEnum.COMMITTED else None,
        promoted_from_id=promoted_from_id,
        created_by_id=user_id,
    )
    session.add(evaluation)
    try:
        await session.flush()
    except IntegrityError as exc:
        translate_integrity_error(exc)
    for term, amount in zip(terms, term_amounts):
        session.add(ItemCostEvaluationTerm(
            workspace_id=workspace_id,
            evaluation_id=evaluation.client_id,
            name=term.name,
            calculation_type=term.calculation_type,
            percent_value=term.percent_value,
            fixed_amount_minor=term.fixed_amount_minor,
            amount_minor=amount,
        ))
    await session.flush()
    if previous is not None:
        await session.execute(
            update(ItemCostEvaluation)
            .where(ItemCostEvaluation.client_id == previous.client_id)
            .values(superseded_by_id=evaluation.client_id)
        )

    if kind is ItemCostEvaluationKindEnum.COMMITTED and valuation is not None and (
        (expected_price, purchase_cost)
        != (valuation.expected_sale_price_minor, valuation.purchase_cost_minor)
    ):
        await write_item_valuation_chain_in_session(
            session,
            workspace_id=workspace_id,
            item_id=item.client_id,
            expected_sale_price_minor=expected_price,
            purchase_cost_minor=purchase_cost,
            currency=valuation.currency,
            created_by_id=user_id,
            now=now,
        )

    if kind is ItemCostEvaluationKindEnum.COMMITTED:
        if source_evaluation is None:
            from_value = _figures(previous)
            description = "Item cost evaluation committed"
        else:
            from_value = _figures(previous)
            description = "Item cost projection promoted"
        await _create_history_record_in_session(
            session=session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=description,
            field_name="item_cost_evaluation",
            from_value=from_value,
            to_value=_figures(evaluation),
            created_by_id=user_id,
        )
    await audit(
        ServiceContext(identity={"workspace_id": workspace_id, "user_id": user_id}, incoming_data={}, session=session),
        audit_event,
        "item_cost_evaluation",
        evaluation.client_id,
    )
    pending_events = []
    if kind is ItemCostEvaluationKindEnum.COMMITTED:
        pending_events.append(build_workspace_event(
            task,
            "item_economics:evaluation-committed",
            extra={"evaluation_id": evaluation.client_id},
        ))
    return evaluation, pending_events


async def commit_item_cost_evaluation(ctx: ServiceContext) -> dict:
    request = parse_commit_item_cost_evaluation_request(ctx.incoming_data)
    kwargs = {
        "expected_sale_price_minor": request.expected_sale_price_minor
        if "expected_sale_price_minor" in ctx.incoming_data else UNSET,
        "purchase_cost_minor": request.purchase_cost_minor
        if "purchase_cost_minor" in ctx.incoming_data else UNSET,
    }
    async with maybe_begin(ctx.session):
        evaluation, pending_events = await _commit_item_cost_evaluation_in_session(
            ctx.session,
            workspace_id=ctx.workspace_id,
            task_id=request.task_client_id,
            user_id=ctx.user_id,
            label=request.label,
            **kwargs,
        )
        terms = list((await ctx.session.scalars(
            select(ItemCostEvaluationTerm).where(
                ItemCostEvaluationTerm.evaluation_id == evaluation.client_id,
            ).order_by(ItemCostEvaluationTerm.created_at.asc(), ItemCostEvaluationTerm.client_id.asc())
        )).all())
    await event_bus.dispatch(pending_events)
    from beyo_manager.domain.item_economics.serializers import serialize_item_cost_evaluation
    return {"evaluation": serialize_item_cost_evaluation(evaluation, terms)}


async def auto_commit_item_cost_evaluation_in_session(
    ctx: ServiceContext,
    *,
    task: Task,
    item: Item | None,
) -> list:
    """Run the best-effort subordinate commit used by ``create_task``; it raises."""
    if item is None:
        logger.info(
            "item_economics.auto_commit_skipped | task_id=%s item_id=%s status=%s",
            task.client_id,
            None,
            "no_primary_item",
        )
        return []

    valuation = await _load_current_valuation(ctx.session, ctx.workspace_id, item.client_id)
    selection, terms = await _load_preview_inputs(ctx, item)
    status = resolve_item_economics_status(valuation, selection, terms)
    if status is not EconomicsStatusEnum.NOT_EVALUATED:
        logger.info(
            "item_economics.auto_commit_skipped | task_id=%s item_id=%s status=%s",
            task.client_id,
            item.client_id,
            status.value,
        )
        return []
    _evaluation, pending_events = await _commit_item_cost_evaluation_in_session(
        ctx.session,
        workspace_id=ctx.workspace_id,
        task_id=task.client_id,
        user_id=ctx.user_id,
    )
    return pending_events
