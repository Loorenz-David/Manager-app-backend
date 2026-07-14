import pytest

from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
from beyo_manager.services.infra.shopify import dimension_migration_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_batch_uses_configurable_namespace_and_maps_user_errors(monkeypatch) -> None:
    calls = []

    async def fake_execute(**kwargs):
        calls.append(kwargs)
        return {"metafieldsSet": {"userErrors": [{"field": ["metafields", "1", "value"], "message": "bad value"}]}}

    monkeypatch.setattr(dimension_migration_client, "execute_shopify_graphql", fake_execute)
    errors = await dimension_migration_client.set_dimension_metafields_batch(
        shop_domain="shop.myshopify.com", access_token_encrypted="encrypted",
        target_namespace="custom", mutations=[
            {"product_gid": "p1", "key": "height_dimension", "value": "v1"},
            {"product_gid": "p2", "key": "width_dimension", "value": "v2"},
        ],
    )
    assert calls[0]["variables"]["metafields"][0]["namespace"] == "custom"
    assert calls[0]["variables"]["metafields"][0]["type"] == "dimension"
    assert errors == [{"product_gid": "p2", "key": "width_dimension", "message": "bad value", "field": ["metafields", "1", "value"]}]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_batch_uses_metafield_identifier_input(monkeypatch) -> None:
    captured = {}

    async def fake_execute(**kwargs):
        captured.update(kwargs)
        return {"metafieldsDelete": {"userErrors": []}}

    monkeypatch.setattr(dimension_migration_client, "execute_shopify_graphql", fake_execute)
    await dimension_migration_client.delete_stale_extension_dimension_batch(
        shop_domain="shop.myshopify.com", access_token_encrypted="encrypted",
        target_namespace="custom", mutations=[{"product_gid": "p1", "key": "extension_dimension"}],
    )
    assert captured["variables"] == {"metafields": [{"ownerId": "p1", "namespace": "custom", "key": "extension_dimension"}]}
    assert "metafieldsDelete" in captured["query"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retryable_transport_error_is_retried(monkeypatch) -> None:
    attempts = 0
    sleeps = []

    async def fake_execute(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ShopifyGraphQLRetryableError("temporary", error_code="timeout")
        return {"metafieldsSet": {"userErrors": []}}

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(dimension_migration_client, "execute_shopify_graphql", fake_execute)
    monkeypatch.setattr(dimension_migration_client.asyncio, "sleep", fake_sleep)
    await dimension_migration_client.set_dimension_metafields_batch(
        shop_domain="shop.myshopify.com", access_token_encrypted="encrypted",
        target_namespace="custom", mutations=[{"product_gid": "p1", "key": "height_dimension", "value": "v1"}],
    )
    assert attempts == 3
    assert sleeps == [1.0, 2.0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_batch_can_resume_at_a_completed_batch_offset(monkeypatch) -> None:
    calls = []

    async def fake_execute(**kwargs):
        calls.append(kwargs["variables"]["metafields"])
        return {"metafieldsSet": {"userErrors": []}}

    monkeypatch.setattr(dimension_migration_client, "execute_shopify_graphql", fake_execute)
    await dimension_migration_client.set_dimension_metafields_batch(
        shop_domain="shop.myshopify.com", access_token_encrypted="encrypted",
        target_namespace="custom", start_offset=1,
        mutations=[
            {"product_gid": "p1", "key": "height_dimension", "value": "v1"},
            {"product_gid": "p2", "key": "height_dimension", "value": "v2"},
        ],
    )
    assert len(calls) == 1
    assert calls[0][0]["ownerId"] == "p2"


@pytest.mark.unit
def test_canonical_quantity_definition_and_product_mapping_are_separate() -> None:
    assert dimension_migration_client.TARGET_TYPES["extensions_quantity"] == "number_integer"
    assert "extension_quantity" not in dimension_migration_client.TARGET_TYPES
    mapped = dimension_migration_client._map_product({
        "id": "p1", "title": "Chair", "handle": "chair",
        "status": "ARCHIVED",
        "legacyDimensions": {"id": "m1", "value": "Depth: 35 cm", "type": "multi_line_text_field"},
        "legacyExtensionQuantity": {"value": "2"},
        "existingExtensionsQuantity": {"value": "2"},
        "variants": {"edges": []},
    })
    assert mapped["legacy"]["extension_quantity"] == "2"
    assert mapped["legacy"]["dimensions"] == "Depth: 35 cm"
    assert mapped["status"] == "ARCHIVED"
    assert mapped["existing"]["extensions_quantity"] == "2"
    assert "extension_quantity" not in mapped["existing"]


@pytest.mark.unit
def test_preflight_requires_plural_canonical_quantity_definition() -> None:
    definitions = {key: {"type": value} for key, value in dimension_migration_client.TARGET_TYPES.items()}
    assert dimension_migration_client.validate_target_metafield_definitions(definitions) == []
    missing = dict(definitions)
    missing.pop("extensions_quantity")
    problems = dimension_migration_client.validate_target_metafield_definitions(missing)
    assert "missing_definition:extensions_quantity" in problems
    assert all("missing_definition:extension_quantity" not in problem for problem in problems)


@pytest.mark.unit
def test_product_query_requests_legacy_dimensions_without_status_filter() -> None:
    assert 'metafield(namespace: "custom", key: "dimensionss") { id value type }' in dimension_migration_client.PRODUCT_DIMENSION_PAGE_QUERY
    assert "status" in dimension_migration_client.PRODUCT_DIMENSION_PAGE_QUERY
    assert "query: \"status:ACTIVE\"" not in dimension_migration_client.PRODUCT_DIMENSION_PAGE_QUERY
