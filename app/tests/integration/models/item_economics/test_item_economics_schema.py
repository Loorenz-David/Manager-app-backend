from __future__ import annotations

import importlib
import inspect as python_inspect
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Numeric, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.item_economics.production_cost_group_section import ProductionCostGroupSection
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
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
    "uix_production_cost_groups_major_category_active",
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


async def _foundation(db_session, *, basis_open=True, model_open=True):
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
    group = ProductionCostGroup(
        workspace_id=workspace.client_id,
        name=f"group {token}",
        major_category=ItemMajorCategoryEnum.WOOD,
        created_by_id=user.client_id,
    )
    db_session.add_all([item, task, group])
    await db_session.flush()
    basis = ProductionCostBasisVersion(
        workspace_id=workspace.client_id, production_cost_group_id=group.client_id,
        effective_to=None if basis_open else date(2099, 1, 1),
        fixed_monthly_cost_minor=1, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("1.00"), planning_utilization_percent=Decimal("1.00"),
        cost_per_worker_minute_minor=Decimal("0.0001"), created_by_id=user.client_id,
    )
    model = CostModelVersion(
        workspace_id=workspace.client_id, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        effective_to=None if model_open else date(2099, 1, 1),
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
        "percent_value": next(
            column for column in inspect(sync).get_columns("cost_model_terms")
            if column["name"] == "percent_value"
        )["type"],
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
    assert isinstance(snapshot["percent_value"], Numeric)
    assert (snapshot["percent_value"].precision, snapshot["percent_value"].scale) == (6, 3)

    type_names = await connection.execute(text(
        "SELECT typname FROM pg_type WHERE typname IN ("
        "'cost_model_term_calculation_type_enum', 'item_cost_evaluation_kind_enum', "
        "'production_cost_basis_version_currency_enum', 'cost_model_version_currency_enum', "
        "'item_valuation_currency_enum', 'business_task_type_enum', "
        "'task_return_source_enum', 'task_state_enum')"
    ))
    assert {row[0] for row in type_names} == {
        "cost_model_term_calculation_type_enum", "item_cost_evaluation_kind_enum",
        "production_cost_basis_version_currency_enum", "cost_model_version_currency_enum",
        "item_valuation_currency_enum", "business_task_type_enum",
        "task_return_source_enum", "task_state_enum",
    }
    task_types = await connection.execute(text(
        "SELECT a.attname, t.typname "
        "FROM pg_attribute AS a "
        "JOIN pg_class AS c ON c.oid = a.attrelid "
        "JOIN pg_type AS t ON t.oid = a.atttypid "
        "WHERE c.relname = 'tasks' AND a.attname IN ('task_type', 'return_source', 'state')"
    ))
    assert dict(task_types.all()) == {
        "task_type": "business_task_type_enum",
        "return_source": "task_return_source_enum",
        "state": "task_state_enum",
    }


def test_downgrade_static_proxy_is_exact():
    migration = importlib.import_module("migrations.versions.90cdd23a828e_item_economics_schema")
    upgrade_source = python_inspect.getsource(migration.upgrade)
    downgrade_source = python_inspect.getsource(migration.downgrade)
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
    dropped_enum_variables = set(re.findall(r"(_[a-z0-9_]+_enum)\.drop\(", downgrade_source))
    dropped_enum_names = {getattr(migration, variable).name for variable in dropped_enum_variables}
    assert dropped_enum_names == new_types
    assert not {migration._business_task_type_enum.name, migration._task_return_source_enum.name, migration._task_state_enum.name} & dropped_enum_names
    assert set(re.findall(r"op\.drop_table\(\s*['\"]([^'\"]+)", downgrade_source)) == set(
        re.findall(r"op\.create_table\(\s*['\"]([^'\"]+)", upgrade_source)
    )


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


async def _assert_c2_second(db_session, first, second, *, conflict):
    db_session.add(first)
    await db_session.flush()
    if conflict:
        with pytest.raises(IntegrityError):
            async with db_session.begin_nested():
                db_session.add(second)
                await db_session.flush()
    else:
        db_session.add(second)
        await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "groups_conflict", "groups_soft_deleted",
        "sections_conflict", "sections_removed",
        "basis_conflict", "basis_closed", "basis_soft_deleted",
        "models_conflict", "models_closed", "models_soft_deleted",
        "purchase_conflict", "purchase_other_type", "purchase_soft_deleted",
        "term_name_conflict", "term_name_soft_deleted", "term_name_other_version",
        "evaluations_conflict", "evaluations_superseded", "evaluations_projection", "evaluations_soft_deleted",
        "valuations_conflict", "valuations_superseded", "valuations_soft_deleted",
        "results_conflict", "results_other_task",
    ],
)
async def test_partial_unique_indexes_enforce_conflicts_and_exclusions(db_session, case):
    workspace, user, item, task, group, basis, model = await _foundation(db_session)
    now = datetime.now(timezone.utc)
    later = date(2099, 1, 1)

    if case == "groups_conflict" or case == "groups_soft_deleted":
        second = ProductionCostGroup(
            workspace_id=workspace.client_id, name=group.name, created_by_id=user.client_id,
            major_category=ItemMajorCategoryEnum.SEAT,
            is_deleted=case == "groups_soft_deleted",
        )
        await _assert_c2_second(db_session, group, second, conflict=case == "groups_conflict")
        return

    if case == "sections_conflict" or case == "sections_removed":
        section = WorkingSection(workspace_id=workspace.client_id, name=f"section {uuid4().hex}")
        second_group = ProductionCostGroup(
            workspace_id=workspace.client_id, name=f"group {uuid4().hex}", created_by_id=user.client_id,
            major_category=ItemMajorCategoryEnum.SEAT,
        )
        db_session.add_all([section, second_group])
        await db_session.flush()
        first = ProductionCostGroupSection(
            workspace_id=workspace.client_id, production_cost_group_id=group.client_id,
            working_section_id=section.client_id, added_by_id=user.client_id,
        )
        second = ProductionCostGroupSection(
            workspace_id=workspace.client_id, production_cost_group_id=second_group.client_id,
            working_section_id=section.client_id, added_by_id=user.client_id,
            removed_at=now if case == "sections_removed" else None,
        )
        await _assert_c2_second(db_session, first, second, conflict=case == "sections_conflict")
        return

    if case in {"basis_conflict", "basis_closed", "basis_soft_deleted"}:
        second = ProductionCostBasisVersion(
            workspace_id=workspace.client_id, production_cost_group_id=group.client_id,
            effective_to=later if case == "basis_closed" else None,
            fixed_monthly_cost_minor=1, currency=ItemCurrencyEnum.SWEDISH_KRONA,
            monthly_paid_hours=Decimal("1"), planning_utilization_percent=Decimal("1"),
            cost_per_worker_minute_minor=Decimal("0.0001"), created_by_id=user.client_id,
            is_deleted=case == "basis_soft_deleted",
        )
        await _assert_c2_second(db_session, basis, second, conflict=case == "basis_conflict")
        return

    if case in {"models_conflict", "models_closed", "models_soft_deleted"}:
        second = CostModelVersion(
            workspace_id=workspace.client_id,
            effective_to=later if case == "models_closed" else None,
            currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id,
            is_deleted=case == "models_soft_deleted",
        )
        await _assert_c2_second(db_session, model, second, conflict=case == "models_conflict")
        return

    if case in {"purchase_conflict", "purchase_other_type", "purchase_soft_deleted"}:
        first = _term(workspace, user, model, name="purchase-first", calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, fixed=None)
        second = _term(
            workspace, user, model, name="purchase-second",
            calculation_type=(CostModelTermCalculationTypeEnum.FIXED_AMOUNT if case == "purchase_other_type" else CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST),
            fixed=1 if case == "purchase_other_type" else None,
            is_deleted=case == "purchase_soft_deleted",
        )
        await _assert_c2_second(db_session, first, second, conflict=case == "purchase_conflict")
        return

    if case in {"term_name_conflict", "term_name_soft_deleted", "term_name_other_version"}:
        first = _term(workspace, user, model, name="same-name")
        if case == "term_name_other_version":
            other_model = CostModelVersion(
                workspace_id=workspace.client_id, effective_to=later,
                currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id,
            )
            db_session.add(other_model)
            await db_session.flush()
            second_model = other_model
        else:
            second_model = model
        second = _term(
            workspace, user, second_model, name="same-name", is_deleted=case == "term_name_soft_deleted"
        )
        await _assert_c2_second(db_session, first, second, conflict=case == "term_name_conflict")
        return

    if case in {"evaluations_conflict", "evaluations_superseded", "evaluations_projection", "evaluations_soft_deleted"}:
        first, *_ = await _evaluation(db_session, kind=ItemCostEvaluationKindEnum.COMMITTED)
        second, *_ = await _evaluation(
            db_session,
            kind=(ItemCostEvaluationKindEnum.PROJECTION if case == "evaluations_projection" else ItemCostEvaluationKindEnum.COMMITTED),
            superseded_at=now if case == "evaluations_superseded" else None,
            is_deleted=case == "evaluations_soft_deleted",
        )
        # _evaluation creates a separate foundation; align the candidate to the first
        # task so the current-evaluation index is the only possible conflict.
        second.task_id = first.task_id
        second.workspace_id = first.workspace_id
        second.item_id = first.item_id
        second.cost_model_version_id = first.cost_model_version_id
        second.production_cost_group_id = first.production_cost_group_id
        second.production_cost_basis_version_id = first.production_cost_basis_version_id
        second.created_by_id = first.created_by_id
        await _assert_c2_second(db_session, first, second, conflict=case == "evaluations_conflict")
        return

    if case in {"valuations_conflict", "valuations_superseded", "valuations_soft_deleted"}:
        first = ItemValuation(
            workspace_id=workspace.client_id, item_id=item.client_id,
            expected_sale_price_minor=0, currency=ItemCurrencyEnum.SWEDISH_KRONA,
            created_by_id=user.client_id,
        )
        second = ItemValuation(
            workspace_id=workspace.client_id, item_id=item.client_id,
            purchase_cost_minor=0, currency=ItemCurrencyEnum.SWEDISH_KRONA,
            created_by_id=user.client_id,
            superseded_at=now if case == "valuations_superseded" else None,
            is_deleted=case == "valuations_soft_deleted",
        )
        await _assert_c2_second(db_session, first, second, conflict=case == "valuations_conflict")
        return

    if case in {"results_conflict", "results_other_task"}:
        evaluation, result_workspace, result_user, result_item, result_task, *_ = await _evaluation(db_session)
        db_session.add(evaluation)
        await db_session.flush()
        first = ItemCostResult(
            workspace_id=result_workspace.client_id, task_id=result_task.client_id, item_id=result_item.client_id,
            evaluation_id=evaluation.client_id, actual_worker_seconds=0,
            actual_worker_minutes=Decimal("0"), consumed_cost_minor=0,
            variance_worker_minutes=Decimal("0"), variance_cost_minor=0,
            task_state_snapshot=TaskStateEnum.PENDING, calculation_version=1,
            computed_at=now,
        )
        second_task = result_task
        if case == "results_other_task":
            second_task = Task(
                client_id=f"tsk_{uuid4().hex}", workspace_id=result_workspace.client_id,
                task_scalar_id=int(uuid4().hex[:8], 16) % 2_000_000_000,
                task_type=TaskTypeEnum.INTERNAL, created_by_id=result_user.client_id,
            )
            db_session.add(second_task)
            await db_session.flush()
        second = ItemCostResult(
            workspace_id=result_workspace.client_id, task_id=second_task.client_id, item_id=result_item.client_id,
            evaluation_id=evaluation.client_id, actual_worker_seconds=0,
            actual_worker_minutes=Decimal("0"), consumed_cost_minor=0,
            variance_worker_minutes=Decimal("0"), variance_cost_minor=0,
            task_state_snapshot=TaskStateEnum.PENDING, calculation_version=1,
            computed_at=now,
        )
        await _assert_c2_second(db_session, first, second, conflict=case == "results_conflict")
        return

    raise AssertionError(f"unhandled C2 case: {case}")


@pytest.mark.asyncio
@pytest.mark.parametrize("field, value, constraint_name, accept", [
    ("fixed_monthly_cost_minor", -1, "ck_pcbv_fixed_monthly_cost_minor_positive", False),
    ("fixed_monthly_cost_minor", 0, "ck_pcbv_fixed_monthly_cost_minor_positive", False),
    ("fixed_monthly_cost_minor", 1, None, True),
    ("cost_per_worker_minute_minor", Decimal("0"), "ck_pcbv_cost_per_worker_minute_minor_positive", False),
    ("cost_per_worker_minute_minor", Decimal("0.0001"), None, True),
    ("monthly_paid_hours", Decimal("0"), "ck_pcbv_monthly_paid_hours_positive", False),
    ("monthly_paid_hours", Decimal("0.01"), None, True),
    ("planning_utilization_percent", Decimal("0"), "ck_pcbv_planning_utilization_percent_positive", False),
    ("planning_utilization_percent", Decimal("0.01"), None, True),
    ("planning_utilization_percent", Decimal("100"), None, True),
    ("planning_utilization_percent", Decimal("100.01"), "ck_pcbv_planning_utilization_percent_max", False),
])
async def test_basis_positive_boundaries(db_session, field, value, constraint_name, accept):
    workspace, user, _, _, group, _, _ = await _foundation(db_session, basis_open=False)
    payload = dict(workspace_id=workspace.client_id, production_cost_group_id=group.client_id, fixed_monthly_cost_minor=1, currency=ItemCurrencyEnum.SWEDISH_KRONA, monthly_paid_hours=Decimal("1"), planning_utilization_percent=Decimal("1"), cost_per_worker_minute_minor=Decimal("0.0001"), created_by_id=user.client_id)
    payload[field] = value
    if accept:
        db_session.add(ProductionCostBasisVersion(**payload))
        await db_session.flush()
    else:
        with pytest.raises(IntegrityError, match=constraint_name):
            async with db_session.begin_nested():
                db_session.add(ProductionCostBasisVersion(**payload))
                await db_session.flush()


@pytest.mark.asyncio
async def test_evaluation_budget_and_allowance_are_intentionally_unchecked(db_session):
    evaluation, *_ = await _evaluation(db_session, production_budget_minor=-500, allowed_worker_minutes=Decimal("-12.50"))
    db_session.add(evaluation)
    await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("percent", "accept", "constraint_name"),
    [
        (Decimal("-0.001"), False, "ck_cost_model_terms_percent_value_non_negative"),
        (Decimal("0"), True, None),
        (Decimal("999.999"), True, None),
        (Decimal("1000"), False, None),
    ],
    ids=["negative-reject", "zero-accept", "max-precision-accept", "numeric-bound-reject"],
)
async def test_percent_boundaries_use_check_and_numeric_type(db_session, percent, accept, constraint_name):
    workspace, user, _, _, _, _, model = await _foundation(db_session)
    term = _term(
        workspace, user, model,
        calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
        percent=percent, fixed=None,
    )
    if accept:
        db_session.add(term)
        await db_session.flush()
    else:
        expected_error = DBAPIError if percent == Decimal("1000") else IntegrityError
        error_context = pytest.raises(expected_error, match=constraint_name) if constraint_name else pytest.raises(expected_error)
        with error_context:
            async with db_session.begin_nested():
                db_session.add(term)
                await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "constraint_name", "accept"),
    [
        ("expected_sale_price_minor", -1, "ck_ice_expected_sale_price_minor_non_negative", False),
        ("expected_sale_price_minor", 0, None, True),
        ("purchase_cost_minor", -1, "ck_ice_purchase_cost_minor_non_negative", False),
        ("purchase_cost_minor", 0, None, True),
        ("purchase_cost_minor", None, None, True),
    ],
)
async def test_evaluation_money_boundaries(db_session, field, value, constraint_name, accept):
    evaluation, *_ = await _evaluation(db_session, **{field: value})
    if accept:
        db_session.add(evaluation)
        await db_session.flush()
    else:
        with pytest.raises(IntegrityError, match=constraint_name):
            async with db_session.begin_nested():
                db_session.add(evaluation)
                await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fixed", "accept"),
    [(-1, False), (0, True)],
    ids=["negative-reject", "zero-accept"],
)
async def test_fixed_amount_money_boundaries(db_session, fixed, accept):
    workspace, user, _, _, _, _, model = await _foundation(db_session)
    term = _term(
        workspace, user, model,
        calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
        fixed=fixed,
    )
    if accept:
        db_session.add(term)
        await db_session.flush()
    else:
        with pytest.raises(IntegrityError, match="ck_cost_model_terms_fixed_amount_minor_non_negative"):
            async with db_session.begin_nested():
                db_session.add(term)
                await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize("actual_worker_seconds, accept", [(-1, False), (0, True)], ids=["negative-reject", "zero-accept"])
async def test_result_actual_worker_seconds_boundaries(db_session, actual_worker_seconds, accept):
    evaluation, workspace, user, item, task, *_ = await _evaluation(db_session)
    db_session.add(evaluation)
    await db_session.flush()
    db_session.add(ItemCostEvaluationTerm(
        workspace_id=workspace.client_id, evaluation_id=evaluation.client_id,
        name="purchase", calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
        amount_minor=0,
    ))
    await db_session.flush()
    result = ItemCostResult(
        workspace_id=workspace.client_id, task_id=task.client_id, item_id=item.client_id,
        evaluation_id=evaluation.client_id, actual_worker_seconds=actual_worker_seconds,
        actual_worker_minutes=Decimal("0"), consumed_cost_minor=0,
        variance_worker_minutes=Decimal("0"), variance_cost_minor=0,
        task_state_snapshot=TaskStateEnum.PENDING, calculation_version=1,
        computed_at=datetime.now(timezone.utc),
    )
    if accept:
        db_session.add(result)
        await db_session.flush()
    else:
        with pytest.raises(IntegrityError, match="ck_item_cost_results_actual_worker_seconds_non_negative"):
            async with db_session.begin_nested():
                db_session.add(result)
                await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    ["negative-sale", "negative-purchase", "both-null", "price-only", "cost-only", "null-currency"],
)
async def test_item_valuation_amount_and_currency_boundaries(db_session, case):
    workspace, user, item, *_ = await _foundation(db_session)
    values = dict(
        workspace_id=workspace.client_id, item_id=item.client_id,
        expected_sale_price_minor=0, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    constraint_name = None
    if case == "negative-sale":
        values["expected_sale_price_minor"] = -1
        constraint_name = "ck_item_valuations_expected_sale_price_minor_non_negative"
    elif case == "negative-purchase":
        values["expected_sale_price_minor"] = None
        values["purchase_cost_minor"] = -1
        constraint_name = "ck_item_valuations_purchase_cost_minor_non_negative"
    elif case == "both-null":
        values["expected_sale_price_minor"] = None
    elif case == "cost-only":
        values["expected_sale_price_minor"] = None
        values["purchase_cost_minor"] = 0
    elif case == "null-currency":
        values["currency"] = None

    valuation = ItemValuation(**values)
    if case in {"price-only", "cost-only"}:
        db_session.add(valuation)
        await db_session.flush()
    else:
        error_context = pytest.raises(IntegrityError, match=constraint_name) if constraint_name else pytest.raises(IntegrityError)
        with error_context:
            async with db_session.begin_nested():
                db_session.add(valuation)
                await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("chain", "window", "accept"),
    [
        ("basis", "equal", False), ("basis", "one-day", True),
        ("basis", "from-null", True), ("basis", "to-null", True),
        ("model", "equal", False), ("model", "one-day", True),
        ("model", "from-null", True), ("model", "to-null", True),
    ],
    ids=["basis-equal", "basis-one-day", "basis-from-null", "basis-to-null", "model-equal", "model-one-day", "model-from-null", "model-to-null"],
)
async def test_effective_windows_enforce_strict_order(db_session, chain, window, accept):
    workspace, user, _, _, group, _, _ = await _foundation(db_session, basis_open=False, model_open=False)
    start = date(2026, 1, 1)
    end = start if window == "equal" else start + timedelta(days=1)
    effective_from = None if window == "from-null" else start
    effective_to = None if window == "to-null" else end
    if chain == "basis":
        row = ProductionCostBasisVersion(
            workspace_id=workspace.client_id, production_cost_group_id=group.client_id,
            effective_from=effective_from, effective_to=effective_to,
            fixed_monthly_cost_minor=1, currency=ItemCurrencyEnum.SWEDISH_KRONA,
            monthly_paid_hours=Decimal("1"), planning_utilization_percent=Decimal("1"),
            cost_per_worker_minute_minor=Decimal("0.0001"), created_by_id=user.client_id,
        )
        constraint_name = "ck_production_cost_basis_versions_effective_window"
    else:
        row = CostModelVersion(
            workspace_id=workspace.client_id, effective_from=effective_from,
            effective_to=effective_to, currency=ItemCurrencyEnum.SWEDISH_KRONA,
            created_by_id=user.client_id,
        )
        constraint_name = "ck_cost_model_versions_effective_window"
    if accept:
        db_session.add(row)
        await db_session.flush()
    else:
        with pytest.raises(IntegrityError, match=constraint_name):
            async with db_session.begin_nested():
                db_session.add(row)
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
