import pytest

from beyo_manager.domain.shopify.metafield_preferences import (
    is_shopify_metafield_definition_gid,
    map_shopify_metafield_definition_node,
    normalize_item_category_ids,
    normalize_search_query,
    normalize_shop_integration_ids,
    parse_only_my_preferences,
)


@pytest.mark.unit
def test_normalize_shop_and_category_ids_dedupes_and_preserves_order() -> None:
    raw = " shpint_b, shpint_a, shpint_b,, shpint_c "
    assert normalize_shop_integration_ids(raw) == ["shpint_b", "shpint_a", "shpint_c"]
    assert normalize_item_category_ids(" icat_2,icat_1, icat_2 ") == ["icat_2", "icat_1"]
    assert normalize_shop_integration_ids("   ") == []


@pytest.mark.unit
def test_metafield_query_param_normalization() -> None:
    assert normalize_search_query("  Seat Height ") == "Seat Height"
    assert normalize_search_query("   ") is None
    assert parse_only_my_preferences("true") is True
    assert parse_only_my_preferences("false") is False
    assert parse_only_my_preferences(True) is True


@pytest.mark.unit
def test_metafield_gid_and_node_mapping() -> None:
    assert is_shopify_metafield_definition_gid("gid://shopify/MetafieldDefinition/123") is True
    assert is_shopify_metafield_definition_gid("gid://shopify/Product/123") is False
    result = map_shopify_metafield_definition_node(
        {
            "id": "gid://shopify/MetafieldDefinition/123",
            "name": "Seat height",
            "namespace": "custom",
            "key": "seat_height",
            "description": "Height",
            "type": {"name": "dimension"},
            "validations": [{"name": "choices", "value": "[\\\"40\\\"]"}],
        }
    )
    assert result.type == "dimension"
    assert result.validations == [{"name": "choices", "value": "[\\\"40\\\"]"}]
