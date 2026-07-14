import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.shopify.requests.delete_shopify_metafield_preferences_request import (
    parse_delete_shopify_metafield_preferences_request,
)


@pytest.mark.unit
def test_delete_request_requires_non_empty_client_ids() -> None:
    with pytest.raises(ValidationError):
        parse_delete_shopify_metafield_preferences_request({"client_ids": []})


@pytest.mark.unit
@pytest.mark.parametrize("value", ["shpmfp_1", {"client_id": "shpmfp_1"}, None])
def test_delete_request_rejects_non_list_client_ids(value) -> None:
    with pytest.raises(ValidationError):
        parse_delete_shopify_metafield_preferences_request({"client_ids": value})


@pytest.mark.unit
def test_delete_request_accepts_one_or_more_ids_and_duplicates() -> None:
    request = parse_delete_shopify_metafield_preferences_request(
        {"client_ids": ["shpmfp_1", "shpmfp_1", "shpmfp_2"]}
    )

    assert request.client_ids == ["shpmfp_1", "shpmfp_1", "shpmfp_2"]
