from __future__ import annotations

import importlib
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import DBAPIError, IntegrityError

from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace


CHECK_NAMES = {
    "ck_pcbv_fixed_monthly_cost_minor_positive",
    "ck_pcbv_cost_per_worker_minute_minor_positive",
    "ck_pcbv_monthly_paid_hours_positive",
    "ck_pcbv_planning_utilization_percent_positive",
    "ck_pcbv_planning_utilization_percent_max",
    "ck_production_cost_basis_versions_effective_window",
    "ck_cost_model_versions_effective_window",
    "ck_cost_model_terms_value_by_type",
    "ck_cost_model_terms_percent_value_non_negative",
    "ck_cost_model_terms_fixed_amount_minor_non_negative",
    "ck_ice_expected_sale_price_minor_non_negative",
    "ck_ice_purchase_cost_minor_non_negative",
    "ck_item_valuations_expected_sale_price_minor_non_negative",
    "ck_item_valuations_purchase_cost_minor_non_negative",
    "ck_item_valuations_amount_present",
    "ck_item_cost_results_actual_worker_seconds_non_negative",
}
INDEX_NAMES = {
    "uix_production_cost_groups_name_active",
    "uix_production_cost_group_sections_active",
    "uix_production_cost_basis_versions_open",
    "uix_cost_model_versions_open",
    "uix_cost_model_terms_purchase_cost",
    "uix_cost_model_terms_name_active",
    "uix_item_cost_evaluations_current",
    "uix_item_valuations_current",
    "uq_item_cost_results_task_id",
}
TABLE_NAMES = {
    "production_cost_groups", "production_cost_group_sections", "production_cost_basis_versions",
    "cost_model_versions", "cost_model_terms", "item_cost_evaluations",
    "item_cost_evaluation_terms", "item_cost_results", "item_valuations",
}


async def _foundation(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"economics {token}")
    user = User(client_id=f"usr_{token}", username=f"economics_{token}", email=f"{token}@example.test", password="test")
    db_session.add_all([workspace, user])
    await db_session.flush()
    item = Item(client_id=f"itm_{token}", workspace_id=workspace.client_id, created_by_id=user.client_id)
    task = Task(
        client_id=f"tsk_{token}", workspace_id=workspace.client_id, task_scalar_id=int(token[:8], 16) % 2_000_000_000,
        task_type=TaskTypeEnum.INTERNAL, created_by_id=user.client_id,
    )
    group = ProductionCostGroup(workspace_id=workspace.client_id, name=f"group {token}", created_by_id=user.client_id)
    db_session.add_all([item, task, group])
    await db_session.flush()
    basis = ProductionCostBasisVersion(
        workspace_id=workspace.client_id, production_cost_group_id=group.client_id,
        fixed_monthly_cost_minor=1, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("1.00"), planning_utilization_percent=Decimal("1.00"),
        cost_per_worker_minute_minor=Decimal("0.0001"), created_by_id=user.client_id,
    )
    model = CostModelVersion(
        workspace_id=workspace.client_id, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    db_session.add_all([basis, model])
    await db_session.flush()
    return workspace, user, item, task, group, basis, model


def _term(workspace, user, model, *, name="term", calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT, percent=None, fixed=0, **changes):
    return CostModelTerm(
        workspace_id=workspace.client_id, cost_model_version_id=model.client_id, name=name,
        calculation_type=calculation_type, percent_value=percent, fixed_amount_minor=fixed,
        created_by_id=user.client_id, **changes,
    )


async def _evaluation(db_session, *, kind=ItemCostEvaluationKindEnum.PROJECTION, **changes):
    workspace, user, item, task, group, basis, model = await _foundation(db_session)
    values = dict(
        workspace_id=workspace.client_id, task_id=task.client_id, item_id=item.client_id, kind=kind,
        task_type_snapshot=TaskTypeEnum.INTERNAL, expected_sale_price_minor=0,
        currency=ItemCurrencyEnum.SWEDISH_KRONA, cost_model_version_id=model.client_id,
        production_cost_group_id=group.client_id, production_cost_basis_version_id=basis.client_id,
        monthly_paid_hours_snapshot=Decimal("1.00"), planning_utilization_percent_snapshot=Decimal("1.00"),
        fixed_monthly_cost_minor_snapshot=1, cost_per_worker_minute_minor_snapshot=Decimal("0.0001"),
        production_budget_minor=0, allowed_worker_minutes=Decimal("0.00"), calculation_version=1,
        created_by_id=user.client_id,
    )
    values.update(changes)
    return ItemCostEvaluation(**values), workspace, user, item, task, group, basis, model


@pytest.mark.asyncio
async def test_schema_inventory_is_closed(db_session):
    connection = await db_session.connection()
    snapshot = await connection.run_sync(lambda sync: {
        "tables": set(inspect(sync).get_table_names()),
        "checks": {check["name"] for table in TABLE_NAMES for check in inspect(sync).get_check_constraints(table)},
        "indexes": {index["name"] for table in TABLE_NAMES for index in inspect(sync).get_indexes(table)},
        "uniques": {item["name"] for item in inspect(sync).get_unique_constraints("item_cost_results")},
        "fks": {fk["name"] for table in TABLE_NAMES for fk in inspect(sync).get_foreign_keys(table)},
    })
    assert TABLE_NAMES <= snapshot["tables"]
    assert snapshot["checks"] & CHECK_NAMES == CHECK_NAMES
    assert snapshot["checks"] - CHECK_NAMES == set()
    assert INDEX_NAMES - {"uq_item_cost_results_task_id"} <= snapshot["indexes"]
    assert "uq_item_cost_results_task_id" in snapshot["uniques"]
    assert {
        "fk_item_cost_evaluations_superseded_by_id", "fk_item_cost_evaluations_promoted_from_id",
        "fk_item_valuations_superseded_by_id",
    } <= snapshot["fks"]


def test_downgrade_static_proxy_is_exact():
    migration = importlib.import_module("migrations.versions.90cdd23a828e_item_economics_schema")
    new_types = {
        migration._cost_model_term_calculation_type_enum.name,
        migration._item_cost_evaluation_kind_enum.name,
        migration._production_cost_basis_version_currency_enum.name,
        migration._cost_model_version_currency_enum.name,
        migration._item_valuation_currency_enum.name,
    }
    assert new_types == {
        "cost_model_term_calculation_type_enum", "item_cost_evaluation_kind_enum",
        "production_cost_basis_version_currency_enum", "cost_model_version_currency_enum",
        "item_valuation_currency_enum",
    }
    assert {migration._business_task_type_enum.name, migration._task_return_source_enum.name, migration._task_state_enum.name}.isdisjoint(new_types)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("calculation_type", "percent", "fixed", "accept"),
    [
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, Decimal("1.000"), None, True),
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, Decimal("1.000"), 1, False),
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, None, None, False),
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, None, 1, False),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, None, 1, True),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, Decimal("1.000"), 1, False),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, None, None, False),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, Decimal("1.000"), None, False),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, None, None, True),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, Decimal("1.000"), None, False),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, None, 1, False),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, Decimal("1.000"), 1, False),
    ],
    ids=[f"{kind.value}-percent-{percent is not None}-fixed-{fixed is not None}" for kind, percent, fixed, _ in [
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, Decimal("1.000"), None, True),
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, Decimal("1.000"), 1, False),
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, None, None, False),
        (CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, None, 1, False),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, None, 1, True),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, Decimal("1.000"), 1, False),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, None, None, False),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, Decimal("1.000"), None, False),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, None, None, True),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, Decimal("1.000"), None, False),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, None, 1, False),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, Decimal("1.000"), 1, False),
    ]],
)
async def test_cost_model_term_type_by_value_matrix(db_session, calculation_type, percent, fixed, accept):
    workspace, user, _, _, _, _, model = await _foundation(db_session)
    term = _term(workspace, user, model, calculation_type=calculation_type, percent=percent, fixed=fixed)
    if accept:
        db_session.add(term)
        await db_session.flush()
    else:
        with pytest.raises(IntegrityError):
            async with db_session.begin_nested():
                db_session.add(term)
                await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize("field, value, error", [
    ("fixed_monthly_cost_minor", 0, IntegrityError),
    ("cost_per_worker_minute_minor", Decimal("0"), IntegrityError),
    ("monthly_paid_hours", Decimal("0"), IntegrityError),
    ("planning_utilization_percent", Decimal("0"), IntegrityError),
    ("planning_utilization_percent", Decimal("100.01"), IntegrityError),
])
async def test_basis_positive_boundaries(db_session, field, value, error):
    workspace, user, _, _, group, _, _ = await _foundation(db_session)
    payload = dict(workspace_id=workspace.client_id, production_cost_group_id=group.client_id, fixed_monthly_cost_minor=1, currency=ItemCurrencyEnum.SWEDISH_KRONA, monthly_paid_hours=Decimal("1"), planning_utilization_percent=Decimal("1"), cost_per_worker_minute_minor=Decimal("0.0001"), created_by_id=user.client_id)
    payload[field] = value
    with pytest.raises(error):
        async with db_session.begin_nested():
            db_session.add(ProductionCostBasisVersion(**payload))
            await db_session.flush()


@pytest.mark.asyncio
async def test_evaluation_budget_and_allowance_are_intentionally_unchecked(db_session):
    evaluation, *_ = await _evaluation(db_session, production_budget_minor=-500, allowed_worker_minutes=Decimal("-12.50"))
    db_session.add(evaluation)
    await db_session.flush()


@pytest.mark.asyncio
async def test_percent_numeric_bound_is_type_error_not_check(db_session):
    workspace, user, _, _, _, _, model = await _foundation(db_session)
    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            db_session.add(_term(workspace, user, model, calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE, percent=Decimal("1000"), fixed=None))
            await db_session.flush()


@pytest.mark.asyncio
async def test_item_valuation_requires_an_amount_and_accepts_each_single_amount(db_session):
    workspace, user, item, *_ = await _foundation(db_session)
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(ItemValuation(workspace_id=workspace.client_id, item_id=item.client_id, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id))
            await db_session.flush()
    db_session.add(ItemValuation(workspace_id=workspace.client_id, item_id=item.client_id, expected_sale_price_minor=0, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id))
    await db_session.flush()


@pytest.mark.asyncio
async def test_result_schema_round_six_columns(db_session):
    connection = await db_session.connection()
    columns = await connection.run_sync(lambda sync: {column["name"]: column for column in inspect(sync).get_columns("item_cost_results")})
    assert columns["task_state_snapshot"]["nullable"] is False
    assert columns["task_closed_at"]["nullable"] is True
    assert "calculation_version" in columns
    assert "created_at" in columns
    assert {"updated_at", "is_deleted"}.isdisjoint(columns)
