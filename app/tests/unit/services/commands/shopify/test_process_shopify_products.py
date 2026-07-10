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
