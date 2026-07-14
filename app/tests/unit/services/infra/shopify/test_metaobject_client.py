import pytest

from beyo_manager.services.infra.shopify.metaobject_client import (
    fetch_shopify_metaobject_definitions_by_ids,
    fetch_shopify_metaobject_entries_by_type,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_metaobject_definitions_by_ids_preserves_missing_ids(monkeypatch):
    async def _fake_execute(**kwargs):
        assert kwargs["variables"] == {"ids": ["definition-1", "definition-2"]}
        return {
            "nodes": [
                {
                    "id": "definition-2",
                    "name": "Backrest type",
                    "type": "shopify--backrest-type",
                    "displayNameKey": "name",
                },
                {"id": "definition-1"},
            ]
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metaobject_client.execute_shopify_graphql",
        _fake_execute,
    )
    result = await fetch_shopify_metaobject_definitions_by_ids(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        definition_ids=["definition-1", "definition-2"],
    )

    assert result["definition-1"] is None
    assert result["definition-2"]["type"] == "shopify--backrest-type"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_metaobject_entries_by_type_paginates_and_normalizes_options(
    monkeypatch,
):
    calls: list[dict] = []

    async def _fake_execute(**kwargs):
        calls.append(kwargs)
        if kwargs["variables"]["after"] is None:
            return {
                "metaobjects": {
                    "nodes": [
                        {
                            "id": "entry-1",
                            "handle": "mesh",
                            "displayName": "Mesh",
                        }
                    ],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                }
            }
        return {
            "metaobjects": {
                "nodes": [
                    {"id": "entry-2", "handle": "padded", "displayName": "Padded"}
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metaobject_client.execute_shopify_graphql",
        _fake_execute,
    )
    result = await fetch_shopify_metaobject_entries_by_type(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        metaobject_type="shopify--backrest-type",
    )

    assert result.options == [
        {
            "id": "entry-1",
            "value": "entry-1",
            "label": "Mesh",
            "handle": "mesh",
        },
        {
            "id": "entry-2",
            "value": "entry-2",
            "label": "Padded",
            "handle": "padded",
        },
    ]
    assert result.has_more is False
    assert result.end_cursor is None
    assert calls[1]["variables"]["after"] == "cursor-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_metaobject_entries_by_type_reports_defensive_truncation(
    monkeypatch,
):
    async def _fake_execute(**kwargs):
        return {
            "metaobjects": {
                "nodes": [{"id": "entry-1", "handle": "one", "displayName": "One"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metaobject_client.execute_shopify_graphql",
        _fake_execute,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.metaobject_client.SHOPIFY_METAOBJECT_ENTRY_MAX",
        1,
    )

    result = await fetch_shopify_metaobject_entries_by_type(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        metaobject_type="shopify--backrest-type",
    )

    assert result.options[0]["id"] == "entry-1"
    assert result.has_more is True
    assert result.end_cursor == "cursor-1"
    assert result.truncated is True
