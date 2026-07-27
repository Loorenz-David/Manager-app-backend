import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.pause_reasons.requests import (
    parse_create_pause_reason_request,
    parse_update_pause_reason_request,
)


def test_create_request_normalizes_name():
    request = parse_create_pause_reason_request(
        {"name": " Lunch ", "pause_type": "personal"}
    )

    assert request.name == "Lunch"


def test_create_request_rejects_internal_fields():
    with pytest.raises(ValidationError):
        parse_create_pause_reason_request(
            {"name": "Lunch", "pause_type": "personal", "slug": "custom"}
        )


def test_update_request_allows_explicit_null_description():
    request = parse_update_pause_reason_request(
        {"client_id": "par_1", "description": None}
    )

    assert request.model_dump(exclude_unset=True) == {"client_id": "par_1", "description": None}
