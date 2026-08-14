from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.item_economics.configuration import EconomicsSelection, resolve_item_economics_status
from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.item_economics.serializers import (
    serialize_item_cost_result,
    serialize_item_cost_result_worker,
    serialize_task_budget_status,
)


def _result() -> SimpleNamespace:
    return SimpleNamespace(
        actual_worker_seconds=120,
        actual_worker_minutes="2.00",
        consumed_cost_minor=30,
        variance_worker_minutes="-1.00",
        variance_cost_minor=-10,
        task_state_snapshot="resolved",
        task_closed_at=None,
        calculation_version="v1",
        computed_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )


def test_worker_result_serializer_has_no_monetary_fields() -> None:
    payload = serialize_item_cost_result_worker(_result())

    assert set(payload) == {
        "actual_worker_minutes",
        "variance_worker_minutes",
        "percent_consumed",
        "task_state_snapshot",
        "computed_at",
    }


def test_manager_result_serializer_retains_monetary_snapshot() -> None:
    payload = serialize_item_cost_result(_result())

    assert payload["consumed_cost_minor"] == 30
    assert payload["variance_cost_minor"] == -10


def test_budget_status_worker_surface_excludes_money() -> None:
    status = SimpleNamespace(
        status=EconomicsStatusEnum.OK,
        item_binding="bound",
        actual_worker_seconds=120,
        actual_worker_minutes="2.00",
        remaining_worker_minutes="8.00",
        percent_consumed="20.00",
        variance_worker_minutes="-8.00",
        production_budget_minor=100,
        allowed_worker_minutes="10.00",
        consumed_cost_minor=30,
        variance_cost_minor=70,
        evaluation_id="eval",
        item_id="item",
        result=_result(),
    )

    payload = serialize_task_budget_status(status, include_monetary=False)

    assert payload["allowed_worker_minutes"] == "10.00"
    assert "production_budget_minor" not in payload
    assert "consumed_cost_minor" not in payload
    assert "variance_cost_minor" not in payload
    assert "evaluation_id" not in payload
    assert "item_id" not in payload


@pytest.mark.parametrize(
    ("authority_row", "selection_status", "valuation", "terms"),
    [
        ("P-V-major-category", EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY, None, []),
        ("P-V-no-cost-group", EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP, None, []),
        ("P-V-ambiguous-cost-group", EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP, None, []),
        ("P-V-no-basis-version", EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION, None, []),
        ("P-V-no-cost-model-version", EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION, None, []),
        ("P-V-item-unvalued", EconomicsStatusEnum.OK, None, []),
        ("P-V-expected-price", EconomicsStatusEnum.OK, SimpleNamespace(expected_sale_price_minor=None, purchase_cost_minor=None, currency=ItemCurrencyEnum.SWEDISH_KRONA), []),
        ("P-V-purchase-cost", EconomicsStatusEnum.OK, SimpleNamespace(expected_sale_price_minor=100, purchase_cost_minor=None, currency=ItemCurrencyEnum.SWEDISH_KRONA), [SimpleNamespace(calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST)]),
        ("P-V-currency", EconomicsStatusEnum.OK, SimpleNamespace(expected_sale_price_minor=100, purchase_cost_minor=50, currency=ItemCurrencyEnum.EURO), []),
        ("P-V-not-evaluated", EconomicsStatusEnum.OK, SimpleNamespace(expected_sale_price_minor=100, purchase_cost_minor=50, currency=ItemCurrencyEnum.SWEDISH_KRONA), []),
    ],
    ids=["P-V-major-category", "P-V-no-cost-group", "P-V-ambiguous-cost-group", "P-V-no-basis-version", "P-V-no-cost-model-version", "P-V-item-unvalued", "P-V-expected-price", "P-V-purchase-cost", "P-V-currency", "P-V-not-evaluated"],
)
def test_c7_readiness_producer_drives_each_status_exactly(authority_row, selection_status, valuation, terms) -> None:
    selection = EconomicsSelection(
        status=selection_status,
        selected_group=SimpleNamespace(client_id="group"),
        basis_version=SimpleNamespace(currency=ItemCurrencyEnum.SWEDISH_KRONA),
        cost_model_version=SimpleNamespace(currency=ItemCurrencyEnum.SWEDISH_KRONA),
    )
    status = resolve_item_economics_status(valuation, selection, terms)
    payload = serialize_task_budget_status(
        SimpleNamespace(
            status=status,
            item_binding="detached",
            actual_worker_seconds=None,
            actual_worker_minutes=None,
            remaining_worker_minutes=None,
            percent_consumed=None,
            variance_worker_minutes=None,
            production_budget_minor=None,
            allowed_worker_minutes=None,
            consumed_cost_minor=None,
            variance_cost_minor=None,
            evaluation_id=None,
            item_id=None,
            result=None,
        ),
        include_monetary=False,
    )

    assert payload["status"] == status.value
    if status not in {EconomicsStatusEnum.OK, EconomicsStatusEnum.INFEASIBLE}:
        assert all(
            payload[field] is None
            for field in (
                "actual_worker_seconds", "actual_worker_minutes", "remaining_worker_minutes",
                "percent_consumed", "variance_worker_minutes", "allowed_worker_minutes",
            )
        )


@pytest.mark.parametrize(
    ("authority_row", "status"),
    [("P-V-infeasible", EconomicsStatusEnum.INFEASIBLE), ("P-V-ok", EconomicsStatusEnum.OK)],
    ids=["P-V-infeasible", "P-V-ok"],
)
def test_c7_committed_evaluation_branch_drives_evaluated_status(authority_row, status) -> None:
    committed = SimpleNamespace(
        status=status,
        item_binding="bound",
        actual_worker_seconds=120,
        actual_worker_minutes="2.00",
        remaining_worker_minutes=None if status is EconomicsStatusEnum.INFEASIBLE else "8.00",
        percent_consumed=None if status is EconomicsStatusEnum.INFEASIBLE else "20.00",
        variance_worker_minutes=None if status is EconomicsStatusEnum.INFEASIBLE else "-8.00",
        production_budget_minor=100,
        allowed_worker_minutes="0.00" if status is EconomicsStatusEnum.INFEASIBLE else "10.00",
        consumed_cost_minor=30,
        variance_cost_minor=70,
        evaluation_id="eval",
        item_id="item",
        result=None,
    )
    payload = serialize_task_budget_status(committed, include_monetary=True)

    assert authority_row.startswith("P-V-")
    assert payload["status"] == status.value
    assert payload["production_budget_minor"] == 100
    if status is EconomicsStatusEnum.INFEASIBLE:
        assert payload["percent_consumed"] is None
