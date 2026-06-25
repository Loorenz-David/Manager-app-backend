from decimal import Decimal
from types import SimpleNamespace

import pytest

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.domain.upholstery.serializers import (
    serialize_upholstery,
    serialize_upholstery_inventory,
    serialize_upholstery_inventory_partial,
)


@pytest.mark.unit
def test_serialize_upholstery_returns_net_available_meters():
    upholstery = SimpleNamespace(
        client_id="uph_1",
        name="Blue Velvet",
        code="BLU-1",
        image_url="https://cdn.example.com/uph-1.jpg",
        favorite=False,
        list_order=0,
    )
    inventory = SimpleNamespace(
        current_stored_amount_meters=Decimal("5.000"),
        current_amount_in_need_meters=Decimal("1.000"),
        inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
    )

    result = serialize_upholstery(upholstery, inventory)

    assert result["current_stored_amount_meters"] == "4.000"
    assert result["image_url"] == "https://cdn.example.com/uph-1.jpg"
    assert result["origin"] == "database"


@pytest.mark.unit
def test_serialize_upholstery_never_returns_negative_available_meters():
    upholstery = SimpleNamespace(
        client_id="uph_2",
        name="White Linen",
        code="WHT-2",
        image_url=None,
        favorite=False,
        list_order=0,
    )
    inventory = SimpleNamespace(
        current_stored_amount_meters=Decimal("1.000"),
        current_amount_in_need_meters=Decimal("3.000"),
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
    )

    result = serialize_upholstery(upholstery, inventory)

    assert result["current_stored_amount_meters"] == "0.000"


@pytest.mark.unit
def test_serialize_upholstery_inventory_partial_includes_upholstery_and_ordered_amount():
    inventory = SimpleNamespace(
        client_id="uin_1",
        workspace_id="ws_1",
        upholstery_id="uph_1",
        inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
        current_stored_amount_meters=Decimal("5.000"),
        current_amount_in_need_meters=Decimal("1.500"),
        current_amount_ordered_meters=Decimal("2.500"),
        updated_at=None,
    )

    result = serialize_upholstery_inventory_partial(
        inventory,
        image_url="https://cdn.example.com/uph-1.jpg",
        upholstery_name="Blue Velvet",
        upholstery_code="BLU-1",
        favorite=True,
    )

    assert result["upholstery_id"] == "uph_1"
    assert result["upholstery_name"] == "Blue Velvet"
    assert result["upholstery_code"] == "BLU-1"
    assert result["favorite"] is True
    assert result["current_amount_in_need_meters"] == "1.500"
    assert result["current_amount_ordered_meters"] == "2.500"
    assert result["image_url"] == "https://cdn.example.com/uph-1.jpg"


@pytest.mark.unit
def test_serialize_upholstery_inventory_partial_handles_null_ordered_amount():
    inventory = SimpleNamespace(
        client_id="uin_2",
        workspace_id="ws_1",
        upholstery_id="uph_2",
        inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
        current_stored_amount_meters=Decimal("5.000"),
        current_amount_in_need_meters=None,
        current_amount_ordered_meters=None,
        updated_at=None,
    )

    result = serialize_upholstery_inventory_partial(inventory)

    assert result["favorite"] is None
    assert result["current_amount_in_need_meters"] is None
    assert result["current_amount_ordered_meters"] is None


@pytest.mark.unit
def test_serialize_upholstery_inventory_includes_upholstery_metadata():
    inventory = SimpleNamespace(
        client_id="uin_3",
        workspace_id="ws_1",
        upholstery_id="uph_3",
        inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
        current_stored_amount_meters=Decimal("5.000"),
        current_amount_in_use_meters=None,
        current_amount_in_need_meters=None,
        current_amount_ordered_meters=Decimal("1.000"),
        total_upholstery_used_meters=None,
        total_upholstery_used_inventory_meters=None,
        total_upholstery_used_surplus_meters=None,
        total_upholstery_surplus_meters=None,
        low_stock_threshold_meters=None,
        minimum_to_have=None,
        maximum_to_have=None,
        projected_inventory_value_minor=None,
        currency=None,
        planning_position=None,
        latest_projection_history_id=None,
        created_at=SimpleNamespace(isoformat=lambda: "2026-06-18T00:00:00+00:00"),
        created_by_id=None,
        updated_at=None,
        updated_by_id=None,
        is_deleted=False,
    )

    result = serialize_upholstery_inventory(
        inventory,
        image_url="https://cdn.example.com/uph-3.jpg",
        upholstery_name="Green Linen",
        upholstery_code="GRN-3",
        favorite=True,
    )

    assert result["upholstery_name"] == "Green Linen"
    assert result["upholstery_code"] == "GRN-3"
    assert result["favorite"] is True
