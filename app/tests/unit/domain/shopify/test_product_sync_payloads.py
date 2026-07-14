import pytest

from beyo_manager.domain.shopify.product_sync_payloads import (
    build_normalized_product_sync_payload,
)


@pytest.mark.unit
def test_build_normalized_product_sync_payload_applies_defaults_and_nested_variant_shape() -> (
    None
):
    payload = build_normalized_product_sync_payload(
        {
            "title": "Chair",
            "description": "Soft chair",
            "tags": [" living ", "", "sale"],
            "product_category": "Seating",
            "price": "199.00",
            "weight": {"value": 1.2, "unit": "kg"},
            "sku": "SKU-123",
            "item_article_number": "BAR-123",
            "metafields": {"origin": "warehouse-1", "priority": 2},
        }
    )

    assert payload["product"] == {
        "title": "Chair",
        "descriptionHtml": "Soft chair",
        "status": "DRAFT",
        "tags": ["living", "sale"],
        "productType": "Seating",
    }
    assert payload["variant"] == {
        "barcode": "BAR-123",
        "price": "199.00",
        "inventoryItem": {
            "sku": "SKU-123",
            "measurement": {"weight": {"value": 1.2, "unit": "KILOGRAMS"}},
        },
    }
    assert payload["metafields"] == [
        {"key": "origin", "type": "single_line_text_field", "value": "warehouse-1"},
        {"key": "priority", "type": "single_line_text_field", "value": "2"},
    ]


@pytest.mark.unit
def test_build_normalized_product_sync_payload_uses_article_number_fallback_for_barcode() -> (
    None
):
    payload = build_normalized_product_sync_payload(
        {
            "title": "Table",
            "status": "active",
            "article_number": "ART-555",
            "metafields": {},
        }
    )

    assert payload["product"]["status"] == "ACTIVE"
    assert payload["variant"]["barcode"] == "ART-555"
    assert "inventoryItem" not in payload["variant"]


@pytest.mark.unit
def test_build_normalized_product_sync_payload_allows_per_metafield_type() -> None:
    payload = build_normalized_product_sync_payload(
        {
            "title": "Table",
            "sku": "SKU-123",
            "metafields": {
                "widthcm": {
                    "type": "dimension",
                    "value": {"value": 120, "unit": "CENTIMETERS"},
                },
                "origin": "warehouse-1",
            },
        }
    )

    assert payload["metafields"] == [
        {
            "key": "widthcm",
            "type": "dimension",
            "value": '{"value":120,"unit":"CENTIMETERS"}',
        },
        {
            "key": "origin",
            "type": "single_line_text_field",
            "value": "warehouse-1",
        },
    ]
