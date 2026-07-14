import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.shopify.requests.create_shopify_metafield_preferences_request import (
    parse_create_shopify_metafield_preferences_request,
)


def _selection(
    definition_id: str,
    *,
    shop_id: str = "shpint_1",
    sequence_order: int = 0,
    client_id: str | None = None,
) -> dict:
    selection = {
        "shop_integration_id": shop_id,
        "shopify_metafield_definition_id": definition_id,
        "sequence_order": sequence_order,
    }
    if client_id is not None:
        selection["client_id"] = client_id
    return selection


@pytest.mark.unit
def test_create_request_allows_multiple_definitions_for_one_shop() -> None:
    request = parse_create_shopify_metafield_preferences_request(
        {
            "item_category_id": "icat_1",
            "preferences": [
                _selection("gid://shopify/MetafieldDefinition/1"),
                _selection("gid://shopify/MetafieldDefinition/2", sequence_order=1),
            ],
        }
    )
    assert len(request.preferences) == 2


@pytest.mark.unit
def test_create_request_preserves_client_id() -> None:
    client_id = "shpmfp_01J00000000000000000000000"
    request = parse_create_shopify_metafield_preferences_request(
        {
            "item_category_id": "icat_1",
            "preferences": [
                _selection(
                    "gid://shopify/MetafieldDefinition/1",
                    client_id=client_id,
                )
            ],
        }
    )
    assert request.preferences[0].client_id == client_id


@pytest.mark.unit
def test_create_request_rejects_duplicate_client_ids() -> None:
    client_id = "shpmfp_01J00000000000000000000000"
    with pytest.raises(ValidationError, match="Duplicate client_id"):
        parse_create_shopify_metafield_preferences_request(
            {
                "item_category_id": "icat_1",
                "preferences": [
                    _selection(
                        "gid://shopify/MetafieldDefinition/1",
                        client_id=client_id,
                    ),
                    _selection(
                        "gid://shopify/MetafieldDefinition/2",
                        client_id=client_id,
                    ),
                ],
            }
        )


@pytest.mark.unit
def test_create_request_rejects_exact_duplicate_selection() -> None:
    with pytest.raises(ValidationError, match="Duplicate preference selection"):
        parse_create_shopify_metafield_preferences_request(
            {
                "item_category_id": "icat_1",
                "preferences": [
                    _selection("gid://shopify/MetafieldDefinition/1"),
                    _selection("gid://shopify/MetafieldDefinition/1", sequence_order=1),
                ],
            }
        )


@pytest.mark.unit
def test_create_request_rejects_malformed_gid_and_negative_sequence() -> None:
    with pytest.raises(ValidationError):
        parse_create_shopify_metafield_preferences_request(
            {
                "item_category_id": "icat_1",
                "preferences": [_selection("gid://shopify/Product/1")],
            }
        )
    with pytest.raises(ValidationError):
        parse_create_shopify_metafield_preferences_request(
            {
                "item_category_id": "icat_1",
                "preferences": [_selection("gid://shopify/MetafieldDefinition/1", sequence_order=-1)],
            }
        )
