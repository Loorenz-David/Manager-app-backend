import pytest

from beyo_manager.domain.shopify.preorder_policy import (
    PREORDER_PRODUCT_STATUS,
    PREORDER_QUANTITY_METAFIELD_KEY,
    PREORDER_QUANTITY_METAFIELD_TYPE,
    build_preorder_quantity_metafield,
)


@pytest.mark.unit
def test_preorder_product_status_is_unlisted() -> None:
    # Not ACTIVE (storefront-visible) and not DRAFT (invisible to sales channels, so invisible
    # to Zettle). Changing this silently breaks one of the two requirements.
    assert PREORDER_PRODUCT_STATUS == "UNLISTED"


@pytest.mark.unit
def test_quantity_metafield_uses_the_merchants_real_definition_shape() -> None:
    assert PREORDER_QUANTITY_METAFIELD_KEY == "quantity"
    # The merchant's definition is a text field, not number_integer.
    assert PREORDER_QUANTITY_METAFIELD_TYPE == "single_line_text_field"


@pytest.mark.unit
def test_single_location_quantity_is_mirrored() -> None:
    assert build_preorder_quantity_metafield([2]) == {
        "type": "single_line_text_field",
        "value": "2",
    }


@pytest.mark.unit
def test_multiple_locations_are_summed() -> None:
    assert build_preorder_quantity_metafield([2, 3])["value"] == "5"


@pytest.mark.unit
def test_zero_quantity_is_representable() -> None:
    assert build_preorder_quantity_metafield([0])["value"] == "0"


@pytest.mark.unit
def test_value_is_a_string_not_a_number() -> None:
    # The definition is single_line_text_field; a bare int would be rejected by Shopify.
    value = build_preorder_quantity_metafield([7])["value"]
    assert isinstance(value, str)
    assert value == "7"


@pytest.mark.unit
def test_accepts_any_iterable_not_just_a_list() -> None:
    # The caller passes a generator over the inventory entries.
    assert build_preorder_quantity_metafield(q for q in (4, 1))["value"] == "5"
