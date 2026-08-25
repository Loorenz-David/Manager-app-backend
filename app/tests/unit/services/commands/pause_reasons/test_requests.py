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

    assert request.model_dump(exclude_unset=True) == {
        "client_id": "par_1",
        "description": None,
    }


def test_create_request_normalizes_link_ids():
    request = parse_create_pause_reason_request(
        {
            "name": "Lunch",
            "pause_type": "personal",
            "linked_user_ids": [" usr_1 ", "usr_1"],
            "linked_working_section_ids": [" wsec_1 "],
        }
    )

    assert request.linked_user_ids == ["usr_1", "usr_1"]
    assert request.linked_working_section_ids == ["wsec_1"]


def test_update_request_distinguishes_omitted_links_from_explicit_clear():
    omitted = parse_update_pause_reason_request({"client_id": "par_1", "name": "Lunch"})
    cleared = parse_update_pause_reason_request(
        {
            "client_id": "par_1",
            "linked_user_ids": [],
            "linked_working_section_ids": [],
        }
    )

    assert "linked_user_ids" not in omitted.model_dump(exclude_unset=True)
    assert cleared.model_dump(exclude_unset=True)["linked_user_ids"] == []
    assert cleared.model_dump(exclude_unset=True)["linked_working_section_ids"] == []
