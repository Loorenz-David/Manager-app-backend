import pytest

from beyo_manager.errors.external_service import (
    ShopifyGraphQLNonRetryableError,
    ShopifyGraphQLRetryableError,
)
from beyo_manager.services.infra.shopify.metafield_definition_client import (
    SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE,
    ShopifyMetafieldDefinitionPage,
    search_shopify_metafield_definitions_by_name_page,
    fetch_shopify_metafield_definition_by_id,
    fetch_shopify_metafield_definitions_by_ids,
    search_shopify_metafield_definitions_by_name,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_definition_by_id_is_a_thin_single_shop_wrapper(
    monkeypatch,
) -> None:
    calls: list[dict] = []

    async def _fake_execute(**kwargs):
        calls.append(kwargs)
        return {
            "node": {
                "id": "gid://shopify/MetafieldDefinition/1",
                "ownerType": "PRODUCT",
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.execute_shopify_graphql",
        _fake_execute,
    )
    result = await fetch_shopify_metafield_definition_by_id(
        shop_domain="shop-a.myshopify.com",
        access_token_encrypted="token-a",
        definition_id="gid://shopify/MetafieldDefinition/1",
    )
    assert result["ownerType"] == "PRODUCT"
    assert calls[0]["shop_domain"] == "shop-a.myshopify.com"
    assert calls[0]["access_token_encrypted"] == "token-a"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batched_definition_lookup_matches_nodes_by_id_and_keeps_missing_ids(
    monkeypatch,
) -> None:
    async def _fake_execute(**kwargs):
        assert kwargs["variables"]["ids"] == [
            "gid://shopify/MetafieldDefinition/1",
            "gid://shopify/MetafieldDefinition/2",
        ]
        return {
            "nodes": [
                {"id": "gid://shopify/MetafieldDefinition/2", "ownerType": "PRODUCT"},
                None,
            ]
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.execute_shopify_graphql",
        _fake_execute,
    )
    result = await fetch_shopify_metafield_definitions_by_ids(
        shop_domain="shop-a.myshopify.com",
        access_token_encrypted="token-a",
        definition_ids=[
            "gid://shopify/MetafieldDefinition/1",
            "gid://shopify/MetafieldDefinition/2",
        ],
    )
    assert result["gid://shopify/MetafieldDefinition/1"] is None
    assert result["gid://shopify/MetafieldDefinition/2"]["ownerType"] == "PRODUCT"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_paginates_per_shop_with_typed_owner_type_variable(
    monkeypatch,
) -> None:
    calls: list[dict] = []

    async def _fake_execute(**kwargs):
        calls.append(kwargs)
        after = kwargs["variables"]["after"]
        if after is None:
            return {
                "metafieldDefinitions": {
                    "nodes": [{"id": "one", "name": "Colour", "ownerType": "PRODUCT"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                }
            }
        return {
            "metafieldDefinitions": {
                "nodes": [{"id": "two", "name": "Seat Height", "ownerType": "PRODUCT"}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.execute_shopify_graphql",
        _fake_execute,
    )
    result = await search_shopify_metafield_definitions_by_name(
        shop_domain="shop-b.myshopify.com",
        access_token_encrypted="token-b",
        search_term="height",
    )
    assert [node["id"] for node in result] == ["two"]
    assert calls[0]["variables"]["ownerType"] == SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE
    assert "query" not in calls[0]["variables"]
    assert calls[1]["variables"]["after"] == "cursor-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_stops_at_limit_in_the_middle_of_a_page(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_page(**kwargs):
        calls.append(kwargs)
        return ShopifyMetafieldDefinitionPage(
            nodes=[
                {"id": str(index), "name": f"Height {index}"} for index in range(25)
            ],
            has_next_page=True,
            end_cursor="cursor-unused",
        )

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.fetch_shopify_product_metafield_definitions_page",
        _fake_page,
    )

    result = await search_shopify_metafield_definitions_by_name(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="token",
        search_term="height",
    )

    assert len(result) == 20
    assert len(calls) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_search_term_lists_product_definitions_up_to_limit(
    monkeypatch,
) -> None:
    async def _fake_page(**kwargs):
        return ShopifyMetafieldDefinitionPage(
            nodes=[
                {"id": "one", "name": "Height"},
                {"id": "two", "name": "Width"},
            ],
            has_next_page=False,
            end_cursor=None,
        )

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.fetch_shopify_product_metafield_definitions_page",
        _fake_page,
    )

    result = await search_shopify_metafield_definitions_by_name(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="token",
        search_term="",
    )

    assert [node["id"] for node in result] == ["one", "two"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_page_returns_offset_page_and_has_more(monkeypatch) -> None:
    async def _fake_page(**kwargs):
        return ShopifyMetafieldDefinitionPage(
            nodes=[
                {"id": str(index), "name": f"Height {index}"} for index in range(25)
            ],
            has_next_page=False,
            end_cursor=None,
        )

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.fetch_shopify_product_metafield_definitions_page",
        _fake_page,
    )

    result = await search_shopify_metafield_definitions_by_name_page(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="token",
        search_term="height",
        offset=20,
    )

    assert [node["id"] for node in result.nodes] == [
        "20",
        "21",
        "22",
        "23",
        "24",
    ]
    assert result.offset == 20
    assert result.limit == 20
    assert result.has_more is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_ignores_definitions_with_missing_or_empty_names(
    monkeypatch,
) -> None:
    async def _fake_page(**kwargs):
        return ShopifyMetafieldDefinitionPage(
            nodes=[{"id": "empty", "name": ""}, {"id": "missing"}],
            has_next_page=False,
            end_cursor=None,
        )

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.fetch_shopify_product_metafield_definitions_page",
        _fake_page,
    )

    result = await search_shopify_metafield_definitions_by_name(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="token",
        search_term="height",
    )

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_definition_lookup_returns_non_metafield_nodes_as_is(monkeypatch) -> None:
    node = {"id": "gid://shopify/Product/1"}

    async def _fake_execute(**kwargs):
        return {"node": node, "nodes": [node]}

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.execute_shopify_graphql",
        _fake_execute,
    )

    single = await fetch_shopify_metafield_definition_by_id(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="token",
        definition_id=node["id"],
    )
    batched = await fetch_shopify_metafield_definitions_by_ids(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="token",
        definition_ids=[node["id"]],
    )

    assert single is node
    assert batched == {node["id"]: node}


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_type", [ShopifyGraphQLRetryableError, ShopifyGraphQLNonRetryableError]
)
async def test_search_propagates_pagination_errors(monkeypatch, error_type) -> None:
    async def _fake_page(**kwargs):
        if kwargs["after"] is None:
            return ShopifyMetafieldDefinitionPage(
                nodes=[], has_next_page=True, end_cursor="cursor-1"
            )
        raise error_type("graphql failure", error_code="graphql_failure")

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metafield_definition_client.fetch_shopify_product_metafield_definitions_page",
        _fake_page,
    )

    with pytest.raises(error_type):
        await search_shopify_metafield_definitions_by_name(
            shop_domain="shop.myshopify.com",
            access_token_encrypted="token",
            search_term="height",
        )
