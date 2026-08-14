from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
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
    ("authority_row", "status"),
    [
        ("P-V-major-category", EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY),
        ("P-V-no-cost-group", EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP),
        ("P-V-ambiguous-cost-group", EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP),
        ("P-V-no-basis-version", EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION),
        ("P-V-no-cost-model-version", EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION),
        ("P-V-item-unvalued", EconomicsStatusEnum.ITEM_UNVALUED),
        ("P-V-expected-price", EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE),
        ("P-V-purchase-cost", EconomicsStatusEnum.ITEM_MISSING_PURCHASE_COST),
        ("P-V-currency", EconomicsStatusEnum.CURRENCY_MISMATCH),
        ("P-V-not-evaluated", EconomicsStatusEnum.NOT_EVALUATED),
        ("P-V-infeasible", EconomicsStatusEnum.INFEASIBLE),
        ("P-V-ok", EconomicsStatusEnum.OK),
    ],
    ids=[
        "P-V-major-category",
        "P-V-no-cost-group",
        "P-V-ambiguous-cost-group",
        "P-V-no-basis-version",
        "P-V-no-cost-model-version",
        "P-V-item-unvalued",
        "P-V-expected-price",
        "P-V-purchase-cost",
        "P-V-currency",
        "P-V-not-evaluated",
        "P-V-infeasible",
        "P-V-ok",
    ],
)
def test_c7_serializes_each_shipped_status_exactly(authority_row, status) -> None:
    assert authority_row.startswith("P-V-")
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
