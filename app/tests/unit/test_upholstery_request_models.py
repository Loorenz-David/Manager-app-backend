from decimal import Decimal

import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.upholstery.requests import (
    parse_create_upholstery_request,
)


@pytest.mark.unit
def test_parse_create_upholstery_request_accepts_inline_category() -> None:
    request = parse_create_upholstery_request(
        {
            "name": "Blue Velvet",
            "current_stored_amount_meters": Decimal("1.000"),
            "create_category": {
                "client_id": "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "name": "Mobeltyger",
                "favorite": True,
            },
        }
    )

    assert request.create_category is not None
    assert request.create_category.client_id == "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert request.create_category.name == "Mobeltyger"
    assert request.create_category.favorite is True


@pytest.mark.unit
def test_parse_create_upholstery_request_rejects_both_category_inputs() -> None:
    with pytest.raises(ValidationError, match="mutually exclusive"):
        parse_create_upholstery_request(
            {
                "name": "Blue Velvet",
                "upholstery_category_id": "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "create_category": {"name": "Mobeltyger"},
            }
        )


@pytest.mark.unit
def test_parse_create_upholstery_request_rejects_blank_inline_category_name() -> None:
    with pytest.raises(ValidationError, match="create_category.name: Value error, name must not be blank"):
        parse_create_upholstery_request(
            {
                "name": "Blue Velvet",
                "create_category": {"name": "   "},
            }
        )
