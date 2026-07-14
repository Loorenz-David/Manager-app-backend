import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.shopify.requests.update_shopify_metafield_preference_sequence_order_request import (
    parse_update_shopify_metafield_preference_sequence_order_request,
)


@pytest.mark.unit
def test_update_sequence_order_request_parses_target_and_position() -> None:
    request = parse_update_shopify_metafield_preference_sequence_order_request(
        {"client_id": "shpmfp_1", "sequence_order": 4}
    )

    assert request.client_id == "shpmfp_1"
    assert request.sequence_order == 4


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"sequence_order": 1},
        {"client_id": "shpmfp_1"},
        {"client_id": "shpmfp_1", "sequence_order": -1},
    ],
)
def test_update_sequence_order_request_rejects_invalid_payload(payload: dict) -> None:
    with pytest.raises(ValidationError):
        parse_update_shopify_metafield_preference_sequence_order_request(payload)
