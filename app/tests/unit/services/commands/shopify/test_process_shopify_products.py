import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.shopify.requests.process_shopify_products_request import (
    parse_process_shopify_products_request,
)


@pytest.mark.unit
def test_parse_process_shopify_products_request_rejects_missing_identity_fields() -> None:
    with pytest.raises(ValidationError, match="At least one of sku, item_article_number, or article_number is required"):
        parse_process_shopify_products_request(
            {
                "items": [
                    {
                        "client_id": "frontend_1",
                        "title": "Chair",
                    }
                ]
            }
        )


@pytest.mark.unit
def test_parse_process_shopify_products_request_rejects_invalid_weight_unit() -> None:
    with pytest.raises(ValidationError, match="unit must be one of: g, kg, lb, oz"):
        parse_process_shopify_products_request(
            {
                "items": [
                    {
                        "client_id": "frontend_1",
                        "title": "Chair",
                        "sku": "SKU-1",
                        "weight": {"value": 1.5, "unit": "stone"},
                    }
                ]
            }
        )


@pytest.mark.unit
def test_parse_process_shopify_products_request_drops_zero_inventory_adjustments() -> None:
    request = parse_process_shopify_products_request(
        {
            "items": [
                {
                    "client_id": "frontend_1",
                    "title": "Chair",
                    "sku": "SKU-1",
                    "inventory_adjustments": [
                        {
                            "shop_integration_id": "shpint_1",
                            "location_id": "gid://shopify/Location/1",
                            "quantity_to_add": 0,
                        }
                    ],
                }
            ]
        }
    )
    assert request.items[0].inventory_adjustments == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "adjustment, message",
    [
        (
            {
                "shop_integration_id": "shpint_1",
                "location_id": "gid://shopify/Location/nope",
                "quantity_to_add": 1,
            },
            "location_id must be a Shopify Location GID",
        ),
        (
            {
                "shop_integration_id": "shpint_1",
                "location_id": "gid://shopify/Location/1",
                "quantity_to_add": -1,
            },
            "quantity_to_add cannot be negative",
        ),
        (
            {
                "shop_integration_id": "shpint_1",
                "location_id": "gid://shopify/Location/1",
                "quantity_to_add": 1,
            },
            "duplicate_inventory_location",
        ),
    ],
)
def test_parse_process_shopify_products_request_rejects_invalid_inventory_adjustments(
    adjustment: dict,
    message: str,
) -> None:
    adjustments = [adjustment, adjustment] if message == "duplicate_inventory_location" else [adjustment]
    with pytest.raises(ValidationError, match=message):
        parse_process_shopify_products_request(
            {
                "items": [
                    {
                        "client_id": "frontend_1",
                        "title": "Chair",
                        "sku": "SKU-1",
                        "inventory_adjustments": adjustments,
                    }
                ]
            }
        )
