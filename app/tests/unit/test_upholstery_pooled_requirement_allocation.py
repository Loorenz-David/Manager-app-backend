from decimal import Decimal
from types import SimpleNamespace

import pytest

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.services.commands.upholstery._pooled_requirement_allocation import (
    allocate_pooled_requirements,
    calculate_pooled_requirement_pool,
)


def _inventory(*, stored: str, in_need: str, ordered: str = "0") -> SimpleNamespace:
    return SimpleNamespace(
        current_stored_amount_meters=Decimal(stored),
        current_amount_in_need_meters=Decimal(in_need),
        current_amount_ordered_meters=Decimal(ordered),
    )


def _requirement(
    item_upholstery_id: str,
    amount: str,
    state: ItemUpholsteryRequirementStateEnum = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
) -> SimpleNamespace:
    return SimpleNamespace(
        item_upholstery_id=item_upholstery_id,
        amount_meters=Decimal(amount),
        state=state,
        ordered_at=None,
        updated_by_id=None,
    )


@pytest.mark.unit
def test_ordered_pool_uses_stored_plus_ordered_coverage_for_candidates():
    inventory = _inventory(stored="5.000", in_need="6.000", ordered="1.000")
    candidates = [_requirement("iup_1", "2.000")]

    running_pool = calculate_pooled_requirement_pool(inventory, candidates, mode="ordered")

    assert running_pool == Decimal("2.000")


@pytest.mark.unit
def test_create_order_allocation_marks_requirement_ordered_when_delta_alone_would_not_fit():
    inventory = _inventory(stored="5.000", in_need="6.000", ordered="1.000")
    candidate = _requirement("iup_1", "2.000")

    resolved = allocate_pooled_requirements(
        inventory=inventory,
        ordered_candidates=[candidate],
        target_state=ItemUpholsteryRequirementStateEnum.ORDERED,
        mode="ordered",
        actor_id="usr_1",
        timestamp_field="ordered_at",
    )

    assert resolved == ["iup_1"]
    assert candidate.state == ItemUpholsteryRequirementStateEnum.ORDERED
    assert candidate.updated_by_id == "usr_1"
    assert candidate.ordered_at is not None


@pytest.mark.unit
def test_stored_pool_after_receipt_marks_eligible_candidate_available():
    inventory = _inventory(stored="6.000", in_need="6.000", ordered="0.000")
    candidate = _requirement("iup_1", "2.000", ItemUpholsteryRequirementStateEnum.ORDERED)

    resolved = allocate_pooled_requirements(
        inventory=inventory,
        ordered_candidates=[candidate],
        target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        mode="stored",
        actor_id="usr_1",
        timestamp_field=None,
    )

    assert resolved == ["iup_1"]
    assert candidate.state == ItemUpholsteryRequirementStateEnum.AVAILABLE
    assert candidate.updated_by_id == "usr_1"


@pytest.mark.unit
def test_candidates_that_do_not_fit_remain_unchanged():
    inventory = _inventory(stored="3.000", in_need="8.000", ordered="2.000")
    large_candidate = _requirement("iup_large", "3.000")

    resolved = allocate_pooled_requirements(
        inventory=inventory,
        ordered_candidates=[large_candidate],
        target_state=ItemUpholsteryRequirementStateEnum.ORDERED,
        mode="ordered",
        actor_id="usr_1",
        timestamp_field="ordered_at",
    )

    assert resolved == []
    assert large_candidate.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    assert large_candidate.updated_by_id is None
    assert large_candidate.ordered_at is None


@pytest.mark.unit
def test_priority_order_consumes_pool_before_lower_priority_candidates():
    inventory = _inventory(stored="3.000", in_need="8.000", ordered="2.000")
    high_priority = _requirement("iup_high", "2.000")
    low_priority = _requirement("iup_low", "3.000")

    resolved = allocate_pooled_requirements(
        inventory=inventory,
        ordered_candidates=[high_priority, low_priority],
        target_state=ItemUpholsteryRequirementStateEnum.ORDERED,
        mode="ordered",
        actor_id="usr_1",
        timestamp_field="ordered_at",
    )

    assert resolved == ["iup_high"]
    assert high_priority.state == ItemUpholsteryRequirementStateEnum.ORDERED
    assert low_priority.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
