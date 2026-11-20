"""`get_item_costs_by_sku` / `get_item_costs_for_pricing_app` against a real database.

Every test stays inside the `db_session` fixture's transaction (flush, never
commit), so the fixture's closing rollback is the cleanup.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.item_economics.calculator import CALCULATION_VERSION
from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PricingApiAuthError
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_item_costs_by_sku import (
    get_item_costs_by_sku,
    get_item_costs_for_pricing_app,
)

from tests.integration.services.commands.item_economics.test_phase7_evaluations import _fixture

pytestmark = pytest.mark.integration

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _ctx(session, workspace_id: str, sku: str | None) -> ServiceContext:
    return ServiceContext(identity={"workspace_id": workspace_id}, incoming_data={"sku": sku}, session=session)


async def _setup(db_session):
    """Phase-7 fixture (wood group + basis + SEK model with one fixed 100 term,
    valuation expected=1000 / purchase=None) plus a SKU on the item."""
    workspace, user, item, task, basis = await _fixture(db_session)
    item.sku = f"SKU-{uuid4().hex[:12]}"
    model = await db_session.scalar(
        select(CostModelVersion).where(CostModelVersion.workspace_id == workspace.client_id)
    )
    valuation = await db_session.scalar(
        select(ItemValuation).where(ItemValuation.item_id == item.client_id)
    )
    await db_session.flush()
    return workspace, user, item, task, basis, model, valuation


def _evaluation(workspace, user, item, task, basis, model, *, budget, committed_at,
                currency=ItemCurrencyEnum.SWEDISH_KRONA) -> ItemCostEvaluation:
    return ItemCostEvaluation(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        item_id=item.client_id,
        kind=ItemCostEvaluationKindEnum.COMMITTED,
        task_type_snapshot=TaskTypeEnum.RETURN,
        expected_sale_price_minor=1000,
        currency=currency,
        cost_model_version_id=model.client_id,
        production_cost_group_id=basis.production_cost_group_id,
        production_cost_basis_version_id=basis.client_id,
        monthly_paid_hours_snapshot=Decimal("160.00"),
        planning_utilization_percent_snapshot=Decimal("80.00"),
        fixed_monthly_cost_minor_snapshot=100000,
        cost_per_worker_minute_minor_snapshot=Decimal("13.0208"),
        production_budget_minor=budget,
        allowed_worker_minutes=Decimal("10.00"),
        calculation_version=CALCULATION_VERSION,
        committed_at=committed_at,
        created_by_id=user.client_id,
    )


def _result(workspace, item, task, evaluation, *, consumed, computed_at) -> ItemCostResult:
    return ItemCostResult(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        item_id=item.client_id,
        evaluation_id=evaluation.client_id,
        actual_worker_seconds=600,
        actual_worker_minutes=Decimal("10.00"),
        consumed_cost_minor=consumed,
        variance_worker_minutes=Decimal("0.00"),
        variance_cost_minor=0,
        task_state_snapshot=TaskStateEnum.RESOLVED,
        calculation_version=CALCULATION_VERSION,
        computed_at=computed_at,
    )


async def _second_task(db_session, workspace, user) -> Task:
    task = Task(
        client_id=f"tsk_{uuid4().hex}",
        workspace_id=workspace.client_id,
        task_scalar_id=2,
        task_type=TaskTypeEnum.RETURN,
        state=TaskStateEnum.RESOLVED,
        created_by_id=user.client_id,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def test_unknown_sku_is_not_found(db_session):
    workspace, *_ = await _setup(db_session)

    with pytest.raises(NotFound):
        await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, "NO-SUCH-SKU"))


async def test_sku_is_workspace_scoped(db_session):
    _workspace, _user, item, *_ = await _setup(db_session)

    with pytest.raises(NotFound):
        await get_item_costs_by_sku(_ctx(db_session, f"ws_{uuid4().hex}", item.sku))


async def test_item_with_nothing_recorded_answers_all_nulls(db_session):
    workspace, user, _item, *_ = await _setup(db_session)
    bare = Item(
        client_id=f"itm_{uuid4().hex}",
        workspace_id=workspace.client_id,
        sku=f"BARE-{uuid4().hex[:8]}",
        created_by_id=user.client_id,
    )
    db_session.add(bare)
    await db_session.flush()

    data = await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, f"  {bare.sku}  "))

    assert data == {
        "sku": bare.sku,
        "currency": None,
        "expectedSalePrice": None,
        "purchaseCost": None,
        "restorationCost": None,
        "otherCosts": None,
    }


async def test_valuation_only_fills_prices_and_other_costs_excluding_the_purchase_term(db_session):
    workspace, user, item, _task, _basis, model, valuation = await _setup(db_session)
    valuation.purchase_cost_minor = 40000
    db_session.add_all([
        CostModelTerm(
            workspace_id=workspace.client_id,
            cost_model_version_id=model.client_id,
            name="vat",
            calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            percent_value=Decimal("20.000"),
            created_by_id=user.client_id,
        ),
        CostModelTerm(
            workspace_id=workspace.client_id,
            cost_model_version_id=model.client_id,
            name="purchase",
            calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
            created_by_id=user.client_id,
        ),
    ])
    await db_session.flush()

    data = await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, item.sku))

    assert data["currency"] == "SEK"
    assert data["expectedSalePrice"]["amount"] == "10.00"
    assert data["purchaseCost"] == {"amount": "400.00", "updatedAt": valuation.created_at.isoformat()}
    # fixed 100 + 20% of 1000 = 300 minor; the 40000 purchase term is not counted.
    assert data["otherCosts"]["amount"] == "3.00"
    assert data["restorationCost"] is None


async def test_superseded_and_deleted_valuations_are_ignored(db_session):
    workspace, user, item, _task, _basis, _model, valuation = await _setup(db_session)
    valuation.superseded_at = T0
    db_session.add(ItemValuation(
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        expected_sale_price_minor=5000,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    ))
    await db_session.flush()

    data = await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, item.sku))
    assert data["expectedSalePrice"]["amount"] == "50.00"

    current = await db_session.scalar(select(ItemValuation).where(
        ItemValuation.item_id == item.client_id, ItemValuation.superseded_at.is_(None)
    ))
    current.is_deleted = True
    await db_session.flush()

    data = await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, item.sku))
    assert data["expectedSalePrice"] is None
    assert data["purchaseCost"] is None
    assert data["otherCosts"] is None


async def test_committed_evaluation_without_results_is_planned(db_session):
    workspace, user, item, task, basis, model, _valuation = await _setup(db_session)
    db_session.add(_evaluation(workspace, user, item, task, basis, model, budget=250, committed_at=T0))
    await db_session.flush()

    data = await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, item.sku))

    assert data["restorationCost"] == {"amount": "2.50", "updatedAt": T0.isoformat(), "source": "planned"}


async def test_results_are_summed_across_tasks_as_actual(db_session):
    workspace, user, item, task, basis, model, _valuation = await _setup(db_session)
    other = await _second_task(db_session, workspace, user)
    first = _evaluation(workspace, user, item, task, basis, model, budget=250, committed_at=T0)
    second = _evaluation(workspace, user, item, other, basis, model, budget=999, committed_at=T0 + timedelta(days=1))
    db_session.add_all([first, second])
    await db_session.flush()
    db_session.add_all([
        _result(workspace, item, task, first, consumed=1200, computed_at=T0 + timedelta(hours=1)),
        _result(workspace, item, other, second, consumed=345, computed_at=T0 + timedelta(days=2)),
    ])
    await db_session.flush()

    data = await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, item.sku))

    assert data["restorationCost"] == {
        "amount": "15.45",
        "updatedAt": (T0 + timedelta(days=2)).isoformat(),
        "source": "actual",
    }


async def test_currency_mismatch_is_a_conflict(db_session):
    workspace, user, item, task, basis, model, _valuation = await _setup(db_session)
    db_session.add(_evaluation(
        workspace, user, item, task, basis, model, budget=250, committed_at=T0, currency=ItemCurrencyEnum.EURO,
    ))
    await db_session.flush()

    with pytest.raises(ConflictError, match="ITEM_COST_CURRENCY_MISMATCH"):
        await get_item_costs_by_sku(_ctx(db_session, workspace.client_id, item.sku))


async def test_pricing_app_entry_authenticates_and_scopes_to_the_configured_workspace(db_session, monkeypatch):
    workspace, _user, item, *_ = await _setup(db_session)
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", "k")
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", workspace.client_id)
    ctx = ServiceContext(identity={}, incoming_data={"headers": {"x-api-key": "k"}, "sku": item.sku}, session=db_session)

    data = await get_item_costs_for_pricing_app(ctx)

    assert data["sku"] == item.sku


async def test_pricing_app_entry_refuses_an_unknown_workspace(db_session, monkeypatch):
    _workspace, _user, item, *_ = await _setup(db_session)
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", "k")
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", f"ws_{uuid4().hex}")
    ctx = ServiceContext(identity={}, incoming_data={"headers": {"x-api-key": "k"}, "sku": item.sku}, session=db_session)

    with pytest.raises(PricingApiAuthError):
        await get_item_costs_for_pricing_app(ctx)
