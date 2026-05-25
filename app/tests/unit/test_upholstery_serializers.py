from decimal import Decimal
from types import SimpleNamespace

import pytest

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery


@pytest.mark.unit
def test_serialize_upholstery_returns_net_available_meters():
    upholstery = SimpleNamespace(
        client_id="uph_1",
        name="Blue Velvet",
        code="BLU-1",
        image_url="https://cdn.example.com/uph-1.jpg",
    )
    inventory = SimpleNamespace(
        current_stored_amount_meters=Decimal("5.000"),
        current_amount_in_need_meters=Decimal("1.000"),
        inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
    )

    result = serialize_upholstery(upholstery, inventory)

    assert result["current_stored_amount_meters"] == "4.000"
    assert result["image_url"] == "https://cdn.example.com/uph-1.jpg"


@pytest.mark.unit
def test_serialize_upholstery_never_returns_negative_available_meters():
    upholstery = SimpleNamespace(
        client_id="uph_2",
        name="White Linen",
        code="WHT-2",
        image_url=None,
    )
    inventory = SimpleNamespace(
        current_stored_amount_meters=Decimal("1.000"),
        current_amount_in_need_meters=Decimal("3.000"),
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
    )

    result = serialize_upholstery(upholstery, inventory)

    assert result["current_stored_amount_meters"] == "0.000"
