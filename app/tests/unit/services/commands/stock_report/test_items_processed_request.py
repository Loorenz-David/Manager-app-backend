"""Plan 9 — C2: `parse_items_processed_body` (master plan §6.5; intention §8B MC-8).

Not a row-by-row transcription of plan 9's C2 rows (that discipline belongs to the
tester); this file builds and exercises the parser's own behaviour.
"""

import json

import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report.items_processed_request import (
    parse_items_processed_body,
)

pytestmark = pytest.mark.unit


def _body(entries: list) -> bytes:
    return json.dumps(entries).encode("utf-8")


def test_c2b_empty_array_is_malformed():
    with pytest.raises(ValidationError) as excinfo:
        parse_items_processed_body(_body([]))
    assert excinfo.value.http_status == 422


def test_c2a_non_array_body_is_malformed():
    with pytest.raises(ValidationError) as excinfo:
        parse_items_processed_body(b"{}")
    assert excinfo.value.http_status == 422


def test_c2c_entry_not_an_object_is_malformed():
    with pytest.raises(ValidationError):
        parse_items_processed_body(_body(["0000612"]))


def test_c2d_missing_article_number_is_malformed():
    with pytest.raises(ValidationError):
        parse_items_processed_body(_body([{}]))


def test_c2e_non_string_article_number_is_malformed():
    with pytest.raises(ValidationError):
        parse_items_processed_body(_body([{"article_number": 612}]))


def test_c2f_blank_article_number_is_malformed():
    with pytest.raises(ValidationError):
        parse_items_processed_body(_body([{"article_number": "  "}]))


def test_c2g_unknown_key_is_ignored_and_the_entry_accepted():
    numbers = parse_items_processed_body(
        _body([{"article_number": "SR-x", "location": "LC1"}])
    )
    assert numbers == ["SR-x"]


def test_c2h_two_malformed_entries_are_both_named():
    body = _body(
        [
            {},
            {"article_number": "SR-x"},
            {"article_number": "  "},
        ]
    )
    with pytest.raises(ValidationError) as excinfo:
        parse_items_processed_body(body)
    assert "entry 0" in excinfo.value.message
    assert "entry 2" in excinfo.value.message
    assert "entry 1" not in excinfo.value.message


def test_numbers_are_echoed_as_received_not_stripped():
    numbers = parse_items_processed_body(_body([{"article_number": " SR-x "}]))
    assert numbers == [" SR-x "]
