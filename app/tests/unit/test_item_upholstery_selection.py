from decimal import Decimal
from types import SimpleNamespace

import pytest

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.domain.items.upholstery_selection import (
    has_positive_amount_meters,
    is_deferred_internal_upholstery,
    should_defer_requirement_creation,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
    ensure_requirement_actions_are_available,
)


def test_should_defer_requirement_creation_for_internal_without_upholstery_id_and_positive_amount():
    assert should_defer_requirement_creation(
        ItemUpholsterySourceEnum.INTERNAL,
        None,
        Decimal("2.500"),
    ) is True


def test_should_not_defer_requirement_creation_for_internal_without_upholstery_id_and_missing_amount():
    assert should_defer_requirement_creation(
        ItemUpholsterySourceEnum.INTERNAL,
        None,
        None,
    ) is False


def test_has_positive_amount_meters_treats_zero_as_not_positive():
    assert has_positive_amount_meters(Decimal("0")) is False


def test_is_deferred_internal_upholstery_requires_internal_missing_selection_and_positive_amount():
    assert is_deferred_internal_upholstery(
        ItemUpholsterySourceEnum.INTERNAL,
        None,
        Decimal("1.000"),
    ) is True
    assert is_deferred_internal_upholstery(
        ItemUpholsterySourceEnum.CUSTOMER,
        None,
        Decimal("1.000"),
    ) is False


def test_requirement_actions_raise_specific_business_error_for_deferred_internal_upholstery():
    iup = SimpleNamespace(
        active_requirement_id=None,
        source=ItemUpholsterySourceEnum.INTERNAL,
        upholstery_id=None,
        amount_meters=Decimal("1.500"),
    )

    with pytest.raises(ValidationError, match="Upholstery must be selected before requirement actions can be performed."):
        ensure_requirement_actions_are_available(iup)


def test_requirement_actions_do_not_raise_for_linked_internal_upholstery():
    iup = SimpleNamespace(
        active_requirement_id="iur_1",
        source=ItemUpholsterySourceEnum.INTERNAL,
        upholstery_id="uph_1",
        amount_meters=Decimal("1.500"),
    )

    ensure_requirement_actions_are_available(iup)
