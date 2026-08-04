from __future__ import annotations

import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.shopify.requests.process_shopify_products_request import (
    ProcessShopifyProductItemRequest,
)
from beyo_manager.services.commands.tasks.requests import (
    ShopifyPreorderSectionInput,
    parse_create_task_request,
)


def _payload(*, quantity: object = 2) -> dict:
    return {
        "task_type": "pre_order",
        "shopify_preorder": {
            "shop_integration_id": "shpint_1",
            "product": {
                "title": "Chair",
                "sku": "SKU-1",
                "price": "5200.00",
                "metafields": {
                    "notes": "handle with care",
                },
            },
            "inventory": [
                {
                    "location_id": "gid://shopify/Location/1",
                    "quantity": quantity,
                }
            ],
        },
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("quantity", "message"),
    [
        (-1, "quantity cannot be negative"),
        (True, "quantity must be an integer"),
        (1_000_001, "quantity cannot exceed 1000000"),
    ],
)
def test_preorder_inventory_quantity_validation(
    quantity: object,
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        parse_create_task_request(_payload(quantity=quantity))


@pytest.mark.unit
def test_preorder_inventory_accepts_zero() -> None:
    request = parse_create_task_request(_payload(quantity=0))

    assert request.shopify_preorder.inventory[0].quantity == 0


@pytest.mark.unit
def test_no_http_request_model_exposes_inventory_mode() -> None:
    assert "inventory_mode" not in ProcessShopifyProductItemRequest.model_fields
    assert "inventory_mode" not in ShopifyPreorderSectionInput.model_fields
    assert "sync_origin" not in ProcessShopifyProductItemRequest.model_fields
    assert "sync_origin" not in ShopifyPreorderSectionInput.model_fields


@pytest.mark.unit
def test_caller_supplied_quantity_metafield_is_accepted() -> None:
    # `custom.quantity` can legitimately differ from the inventory the pre-order writes (e.g. a
    # pack size), so the caller may set it explicitly; it's only defaulted from inventory when
    # omitted (see _create_preorder_sync_item_in_session).
    payload = _payload()
    payload["shopify_preorder"]["product"]["metafields"]["quantity"] = {
        "type": "single_line_text_field",
        "value": "6",
    }

    request = parse_create_task_request(payload)

    assert request.shopify_preorder.product.metafields["quantity"] == {
        "type": "single_line_text_field",
        "value": "6",
    }


@pytest.mark.unit
def test_section_level_quantity_metafield_is_accepted() -> None:
    payload = _payload()
    payload["shopify_preorder"]["metafields"] = {
        "quantity": {
            "type": "single_line_text_field",
            "value": "6",
        }
    }

    request = parse_create_task_request(payload)

    assert request.shopify_preorder.metafields["quantity"] == {
        "type": "single_line_text_field",
        "value": "6",
    }


@pytest.mark.unit
def test_other_metafields_are_still_accepted() -> None:
    request = parse_create_task_request(_payload())

    assert request.shopify_preorder.product.metafields == {"notes": "handle with care"}


@pytest.mark.unit
def test_section_level_metafields_are_accepted() -> None:
    payload = _payload()
    payload["shopify_preorder"]["product"].pop("metafields")
    payload["shopify_preorder"]["metafields"] = {
        "notes": "handle with care",
        "finish": {
            "type": "single_line_text_field",
            "value": "oiled oak",
        },
    }

    request = parse_create_task_request(payload)

    assert request.shopify_preorder.metafields == {
        "notes": "handle with care",
        "finish": {
            "type": "single_line_text_field",
            "value": "oiled oak",
        },
    }


@pytest.mark.unit
def test_duplicate_metafield_keys_across_section_and_product_are_rejected() -> None:
    payload = _payload()
    payload["shopify_preorder"]["metafields"] = {"notes": "top level"}

    with pytest.raises(
        ValidationError,
        match="must be supplied either at the section level or under product",
    ):
        parse_create_task_request(payload)
