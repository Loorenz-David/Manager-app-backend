import pytest

from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
from beyo_manager.services.infra.shopify.metaobject_client import (
    ShopifyMetaobjectEntriesResult,
)
from beyo_manager.services.queries.shopify.enrich_shopify_metafield_references import (
    enrich_shopify_metafield_definitions,
)


def _reference_definition(
    definition_id: str,
    *,
    metafield_type: str = "metaobject_reference",
    metaobject_definition_id: str = "gid://shopify/MetaobjectDefinition/1",
) -> dict:
    return {
        "id": definition_id,
        "ownerType": "PRODUCT",
        "name": "Backrest type",
        "type": {"name": metafield_type},
        "validations": [
            {"name": "metaobject_definition_id", "value": metaobject_definition_id}
        ],
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enriches_single_and_multiple_reference_definitions_and_reuses_entries(
    monkeypatch,
):
    definitions = {
        "metafield-1": _reference_definition("metafield-1"),
        "metafield-2": _reference_definition(
            "metafield-2", metafield_type="list.metaobject_reference"
        ),
        "metafield-3": _reference_definition("metafield-3"),
        "plain": {
            "id": "plain",
            "type": {"name": "single_line_text_field"},
            "validations": [],
        },
    }
    definition_calls: list[list[str]] = []
    entry_calls: list[str] = []

    async def _fake_definitions(**kwargs):
        definition_calls.append(kwargs["definition_ids"])
        return {
            "gid://shopify/MetaobjectDefinition/1": {
                "id": "gid://shopify/MetaobjectDefinition/1",
                "name": "Backrest type",
                "type": "shopify--backrest-type",
                "displayNameKey": "name",
            }
        }

    async def _fake_entries(**kwargs):
        entry_calls.append(kwargs["metaobject_type"])
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
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_definitions_by_ids",
        _fake_definitions,
    )
    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_entries_by_type",
        _fake_entries,
    )

    await enrich_shopify_metafield_definitions(
        definitions=definitions,
        shop_integration_id="shop-integration-1",
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_metaobject_definitions", "read_metaobjects"],
    )

    assert definition_calls == [["gid://shopify/MetaobjectDefinition/1"]]
    assert entry_calls == ["shopify--backrest-type"]
    assert definitions["metafield-1"]["reference_options"]["selection_mode"] == "single"
    assert (
        definitions["metafield-2"]["reference_options"]["selection_mode"] == "multiple"
    )
    assert (
        definitions["metafield-3"]["reference_options"]["options"][0]["label"] == "Mesh"
    )
    assert "reference_options" not in definitions["plain"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_validation_and_missing_definition_are_unavailable(monkeypatch):
    definitions = {
        "missing-validation": _reference_definition("missing-validation"),
        "missing-definition": _reference_definition(
            "missing-definition",
            metaobject_definition_id="gid://shopify/MetaobjectDefinition/404",
        ),
    }
    definitions["missing-validation"]["validations"] = []

    async def _fake_definitions(**kwargs):
        return {kwargs["definition_ids"][0]: None}

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_definitions_by_ids",
        _fake_definitions,
    )
    await enrich_shopify_metafield_definitions(
        definitions=definitions,
        shop_integration_id="shop-integration-1",
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_metaobject_definitions", "read_metaobjects"],
    )

    assert (
        definitions["missing-validation"]["reference_options"]["unavailable_reason"]
        == "missing_metaobject_definition_id"
    )
    assert (
        definitions["missing-definition"]["reference_options"]["unavailable_reason"]
        == "metaobject_definition_not_found"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_scope_and_entry_failure_do_not_look_like_empty_options(
    monkeypatch,
):
    definitions = {
        "missing-scope": _reference_definition("missing-scope"),
    }
    definition_calls = 0

    async def _unexpected_definitions(**kwargs):
        nonlocal definition_calls
        definition_calls += 1
        raise AssertionError("definition lookup must not run without its scope")

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_definitions_by_ids",
        _unexpected_definitions,
    )
    await enrich_shopify_metafield_definitions(
        definitions=definitions,
        shop_integration_id="shop-integration-1",
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_products"],
    )
    assert definition_calls == 0
    assert (
        definitions["missing-scope"]["reference_options"]["unavailable_reason"]
        == "metaobject_definition_inaccessible"
    )

    definitions = {"entry-failure": _reference_definition("entry-failure")}

    async def _fake_definitions(**kwargs):
        return {
            kwargs["definition_ids"][0]: {
                "id": kwargs["definition_ids"][0],
                "name": "Backrest type",
                "type": "shopify--backrest-type",
            }
        }

    async def _failed_entries(**kwargs):
        raise ShopifyGraphQLRetryableError("temporary", error_code="timeout")

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_definitions_by_ids",
        _fake_definitions,
    )
    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.enrich_shopify_metafield_references.fetch_shopify_metaobject_entries_by_type",
        _failed_entries,
    )
    await enrich_shopify_metafield_definitions(
        definitions=definitions,
        shop_integration_id="shop-integration-1",
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_metaobject_definitions", "read_metaobjects"],
    )
    options = definitions["entry-failure"]["reference_options"]
    assert options["options"] == []
    assert options["availability"] == "unavailable"
    assert options["unavailable_reason"] == "metaobject_entries_unavailable"
