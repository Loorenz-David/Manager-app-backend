from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_metafield_preference import (
    ShopifyMetafieldPreference,
)
from beyo_manager.models.tables.shopify.shopify_shop_integration import (
    ShopifyShopIntegration,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.metafield_definition_client import (
    ShopifyMetafieldDefinitionSearchPage,
)
from beyo_manager.services.infra.shopify.metaobject_client import (
    ShopifyMetaobjectEntriesResult,
)
from beyo_manager.services.queries.shopify.get_shopify_metafield_preferences import (
    get_shopify_metafield_preferences,
)


def _gid(value: str) -> str:
    return f"gid://shopify/MetafieldDefinition/{value}"


async def _seed_fixture(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"query-user-{suffix}",
        email=f"query-user-{suffix}@example.com",
        password="hashed",
    )
    category_a = ItemCategory(
        client_id=f"itc_{suffix}_a",
        workspace_id=workspace.client_id,
        name=f"Category A {suffix}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=user.client_id,
    )
    category_b = ItemCategory(
        client_id=f"itc_{suffix}_b",
        workspace_id=workspace.client_id,
        name=f"Category B {suffix}",
        major_category=ItemMajorCategoryEnum.WOOD,
        created_by_id=user.client_id,
    )
    now = datetime.now(timezone.utc)
    shop_a = ShopifyShopIntegration(
        client_id=f"shpint_{suffix}_a",
        workspace_id=workspace.client_id,
        shop_domain=f"query-a-{suffix}.myshopify.com",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        api_version="2026-01",
        access_token_encrypted="query-token-a",
        created_at=now,
        updated_at=now,
    )
    shop_b = ShopifyShopIntegration(
        client_id=f"shpint_{suffix}_b",
        workspace_id=workspace.client_id,
        shop_domain=f"query-b-{suffix}.myshopify.com",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        api_version="2026-01",
        access_token_encrypted="query-token-b",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all([category_a, category_b, shop_a, shop_b])
    await db_session.commit()
    return workspace, user, category_a, category_b, shop_a, shop_b


def _preference(
    *,
    suffix: str,
    workspace_id: str,
    shop_id: str,
    category_id: str,
    definition_id: str,
    sequence_order: int,
    user_id: str,
) -> ShopifyMetafieldPreference:
    return ShopifyMetafieldPreference(
        client_id=f"shpmfp_{suffix}_{uuid4().hex[:6]}",
        workspace_id=workspace_id,
        shop_integration_id=shop_id,
        item_category_id=category_id,
        shopify_metafield_definition_id=definition_id,
        sequence_order=sequence_order,
        created_by_id=user_id,
    )


def _ctx(
    db_session, *, workspace_id: str, user_id: str, query_params: dict
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "admin",
        },
        incoming_data={},
        query_params=query_params,
        session=db_session,
    )


def _definition(definition_id: str, *, name: str) -> dict:
    return {
        "id": definition_id,
        "ownerType": "PRODUCT",
        "name": name,
        "namespace": "custom",
        "key": name.lower().replace(" ", "_"),
        "description": None,
        "type": {"name": "single_line_text_field"},
        "validations": [],
    }


@pytest.mark.integration
async def test_category_query_batches_per_shop_groups_results_and_preserves_order(
    db_session, monkeypatch
) -> None:
    workspace, user, category_a, category_b, shop_a, shop_b = await _seed_fixture(
        db_session
    )
    suffix = uuid4().hex[:8]
    shared = _gid(f"shared-{suffix}")
    a_only = _gid(f"a-only-{suffix}")
    b_only = _gid(f"b-only-{suffix}")
    db_session.add_all(
        [
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_id=shop_a.client_id,
                category_id=category_a.client_id,
                definition_id=shared,
                sequence_order=2,
                user_id=user.client_id,
            ),
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_id=shop_a.client_id,
                category_id=category_a.client_id,
                definition_id=a_only,
                sequence_order=1,
                user_id=user.client_id,
            ),
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_id=shop_b.client_id,
                category_id=category_a.client_id,
                definition_id=shared,
                sequence_order=0,
                user_id=user.client_id,
            ),
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_id=shop_b.client_id,
                category_id=category_b.client_id,
                definition_id=b_only,
                sequence_order=3,
                user_id=user.client_id,
            ),
        ]
    )
    await db_session.commit()
    calls: list[dict] = []

    async def _fake_fetch(**kwargs):
        calls.append(kwargs)
        if kwargs["shop_domain"] == shop_a.shop_domain:
            return {shared: None, a_only: _definition(a_only, name="A only")}
        return {
            shared: _definition(shared, name="Shared B"),
            b_only: _definition(b_only, name="B only"),
        }

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.fetch_shopify_metafield_definitions_by_ids",
        _fake_fetch,
    )
    result = await get_shopify_metafield_preferences(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            query_params={
                "shop_integration_ids": f"{shop_b.client_id},{shop_a.client_id}",
                "item_category_ids": category_a.client_id,
            },
        )
    )

    assert [shop["shop_integration_id"] for shop in result["shops"]] == [
        shop_b.client_id,
        shop_a.client_id,
    ]
    assert len(calls) == 2
    assert calls[0]["definition_ids"] == [shared]
    assert calls[1]["definition_ids"] == [a_only, shared]
    shop_a_result = next(
        shop
        for shop in result["shops"]
        if shop["shop_integration_id"] == shop_a.client_id
    )
    shop_b_result = next(
        shop
        for shop in result["shops"]
        if shop["shop_integration_id"] == shop_b.client_id
    )
    assert shop_a_result["unavailable_definition_ids"] == [shared]
    assert shop_b_result["unavailable_definition_ids"] == []
    shop_a_category = next(
        item
        for item in shop_a_result["item_categories"]
        if item["item_category_id"] == category_a.client_id
    )
    assert [
        item["sequence_order"] for item in shop_a_category["metafield_preferences"]
    ] == [1]
    assert [
        item["sequence_order"]
        for item in next(
            item
            for item in shop_b_result["item_categories"]
            if item["item_category_id"] == category_a.client_id
        )["metafield_preferences"]
    ] == [0]


@pytest.mark.integration
async def test_empty_category_does_not_trigger_shopify_definition_search(
    db_session, monkeypatch
) -> None:
    workspace, user, _category_a, category_b, shop_a, _shop_b = await _seed_fixture(
        db_session
    )
    calls: list[dict] = []

    async def _fake_search(**kwargs):
        calls.append(kwargs)
        raise AssertionError(
            "Empty category lookup must not search Shopify definitions"
        )

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.search_shopify_metafield_definitions_by_name_page",
        _fake_search,
    )
    result = await get_shopify_metafield_preferences(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            query_params={
                "shop_integration_ids": shop_a.client_id,
                "item_category_ids": category_b.client_id,
            },
        )
    )

    shop_result = result["shops"][0]
    assert shop_result["item_categories"] == [
        {"item_category_id": category_b.client_id, "metafield_preferences": []}
    ]
    assert shop_result["search_results"] == []
    assert shop_result["search_pagination"] == {
        "offset": 0,
        "limit": 20,
        "has_more": False,
        "next_offset": None,
    }
    assert calls == []


@pytest.mark.integration
async def test_invalid_requested_integration_fails_without_partial_response(
    db_session,
) -> None:
    workspace, user, category_a, _category_b, shop_a, _shop_b = await _seed_fixture(
        db_session
    )
    with pytest.raises(NotFound):
        await get_shopify_metafield_preferences(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                query_params={
                    "shop_integration_ids": f"{shop_a.client_id},shpint_missing",
                    "item_category_ids": category_a.client_id,
                },
            )
        )


@pytest.mark.integration
async def test_search_runs_independently_per_shop_and_ignores_only_my_preferences(
    db_session, monkeypatch
) -> None:
    workspace, user, _category_a, _category_b, shop_a, shop_b = await _seed_fixture(
        db_session
    )
    calls: list[str] = []

    async def _fake_search(**kwargs):
        calls.append(kwargs["shop_domain"])
        return ShopifyMetafieldDefinitionSearchPage(
            nodes=[
                _definition(
                    _gid(kwargs["shop_domain"]), name=f"Result {kwargs['shop_domain']}"
                )
            ],
            offset=kwargs["offset"],
            limit=20,
            has_more=True,
        )

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.search_shopify_metafield_definitions_by_name_page",
        _fake_search,
    )
    result = await get_shopify_metafield_preferences(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            query_params={
                "shop_integration_ids": f"{shop_a.client_id},{shop_b.client_id}",
                "q": "result",
                "search_offset": "20",
                "only_my_preferences": "true",
            },
        )
    )
    assert calls == [shop_a.shop_domain, shop_b.shop_domain]
    assert [len(shop["search_results"]) for shop in result["shops"]] == [1, 1]
    assert [shop["search_pagination"] for shop in result["shops"]] == [
        {"offset": 20, "limit": 20, "has_more": True, "next_offset": 40},
        {"offset": 20, "limit": 20, "has_more": True, "next_offset": 40},
    ]
    assert result["shops"][0]["search_results"][0][
        "shopify_metafield_definition_id"
    ] == _gid(shop_a.shop_domain)
    assert result["shops"][1]["search_results"][0][
        "shopify_metafield_definition_id"
    ] == _gid(shop_b.shop_domain)


@pytest.mark.integration
async def test_search_failure_for_one_shop_fails_the_whole_request(
    db_session, monkeypatch
) -> None:
    workspace, user, _category_a, _category_b, shop_a, shop_b = await _seed_fixture(
        db_session
    )

    async def _fake_search(**kwargs):
        if kwargs["shop_domain"] == shop_b.shop_domain:
            raise ShopifyGraphQLRetryableError("temporary", error_code="timeout")
        return ShopifyMetafieldDefinitionSearchPage(
            nodes=[_definition(_gid("search-success"), name="Result")],
            offset=kwargs["offset"],
            limit=20,
            has_more=False,
        )

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.search_shopify_metafield_definitions_by_name_page",
        _fake_search,
    )
    with pytest.raises(ShopifyGraphQLRetryableError):
        await get_shopify_metafield_preferences(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                query_params={
                    "shop_integration_ids": f"{shop_a.client_id},{shop_b.client_id}",
                    "q": "result",
                },
            )
        )


@pytest.mark.integration
async def test_saved_and_search_reference_definitions_are_enriched_once_per_shop(
    db_session, monkeypatch
) -> None:
    workspace, user, category_a, _category_b, shop_a, _shop_b = await _seed_fixture(
        db_session
    )
    shop_a.granted_scopes = ["read_metaobject_definitions", "read_metaobjects"]
    definition_id = _gid("reference-definition")
    db_session.add(
        _preference(
            suffix=uuid4().hex[:8],
            workspace_id=workspace.client_id,
            shop_id=shop_a.client_id,
            category_id=category_a.client_id,
            definition_id=definition_id,
            sequence_order=1,
            user_id=user.client_id,
        )
    )
    await db_session.commit()

    definition = _definition(definition_id, name="Backrest type")
    definition["type"] = {"name": "list.metaobject_reference"}
    definition["validations"] = [
        {
            "name": "metaobject_definition_id",
            "value": "gid://shopify/MetaobjectDefinition/1",
        }
    ]
    definition_calls: list[dict] = []
    entry_calls: list[dict] = []

    async def _fake_fetch(**kwargs):
        definition_calls.append(kwargs)
        return {definition_id: definition}

    async def _fake_search(**kwargs):
        return ShopifyMetafieldDefinitionSearchPage(
            nodes=[dict(definition)],
            offset=kwargs["offset"],
            limit=20,
            has_more=False,
        )

    async def _fake_metaobject_definitions(**kwargs):
        return {
            "gid://shopify/MetaobjectDefinition/1": {
                "id": "gid://shopify/MetaobjectDefinition/1",
                "name": "Backrest type",
                "type": "shopify--backrest-type",
                "displayNameKey": "name",
            }
        }

    async def _fake_entries(**kwargs):
        entry_calls.append(kwargs)
        return ShopifyMetaobjectEntriesResult(
            options=[
                {
                    "id": "gid://shopify/Metaobject/1",
                    "value": "gid://shopify/Metaobject/1",
                    "label": "Mesh",
                    "handle": "mesh",
                }
            ],
            has_more=False,
            end_cursor=None,
            truncated=False,
        )

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.fetch_shopify_metafield_definitions_by_ids",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.search_shopify_metafield_definitions_by_name_page",
        _fake_search,
    )
    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_definitions_by_ids",
        _fake_metaobject_definitions,
    )
    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_entries_by_type",
        _fake_entries,
    )

    result = await get_shopify_metafield_preferences(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            query_params={
                "shop_integration_ids": shop_a.client_id,
                "item_category_ids": category_a.client_id,
                "q": "backrest",
            },
        )
    )
    shop_result = result["shops"][0]
    saved = shop_result["item_categories"][0]["metafield_preferences"][0]
    searched = shop_result["search_results"][0]
    assert saved["reference_options"]["selection_mode"] == "multiple"
    assert searched["reference_options"]["options"][0]["label"] == "Mesh"
    assert len(definition_calls) == 1
    assert len(entry_calls) == 1
