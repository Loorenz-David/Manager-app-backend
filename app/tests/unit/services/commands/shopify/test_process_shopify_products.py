import pytest
from types import SimpleNamespace

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.shopify import process_shopify_products as module
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


@pytest.mark.unit
def test_product_image_reference_is_xor_and_https() -> None:
    base = {
        "items": [
            {
                "client_id": "frontend_1",
                "title": "Chair",
                "sku": "SKU-1",
                "image_id": "img_1",
                "image_url": "https://images.example.com/chair.webp",
            }
        ]
    }
    with pytest.raises(ValidationError, match="mutually exclusive"):
        parse_process_shopify_products_request(base)

    base["items"][0].pop("image_id")
    base["items"][0]["image_url"] = "http://images.example.com/chair.webp"
    with pytest.raises(ValidationError, match="absolute HTTPS URL"):
        parse_process_shopify_products_request(base)


class _ImageRows:
    def __init__(self, images):
        self._images = images

    def scalars(self):
        return self

    def all(self):
        return self._images


class _ImageSession:
    def __init__(self, images):
        self._images = images

    async def execute(self, _statement):
        return _ImageRows(self._images)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("image", "message"),
    [
        (
            SimpleNamespace(
                client_id="img_1",
                file_size_bytes=20 * 1024 * 1024 + 1,
                width_px=100,
                height_px=100,
            ),
            "20 MB",
        ),
        (
            SimpleNamespace(
                client_id="img_1",
                file_size_bytes=100,
                width_px=5_001,
                height_px=1,
            ),
            "25 MP or 5000×5000",
        ),
        (
            SimpleNamespace(
                client_id="img_1",
                file_size_bytes=100,
                width_px=5_000,
                height_px=5_001,
            ),
            "25 MP or 5000×5000",
        ),
    ],
)
async def test_image_limits_are_checked_before_enqueue(image, message) -> None:
    request = parse_process_shopify_products_request(
        {
            "items": [
                {
                    "client_id": "frontend_1",
                    "title": "Chair",
                    "sku": "SKU-1",
                    "image_id": "img_1",
                }
            ]
        }
    )
    ctx = SimpleNamespace(
        session=_ImageSession([image]),
    )

    with pytest.raises(ValidationError, match=message):
        await module._validate_image_limits(ctx, request)
