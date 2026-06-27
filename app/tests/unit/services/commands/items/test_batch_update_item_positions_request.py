import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.items.requests import parse_batch_update_item_positions_request


def _entry(index: int) -> dict:
    return {"client_id": f"itm_{index}", "item_position": f"A-{index:02d}"}


@pytest.mark.unit
def test_parse_batch_update_item_positions_request_accepts_valid_entries():
    request = parse_batch_update_item_positions_request({"entries": [_entry(1), _entry(2)]})

    assert [entry.client_id for entry in request.entries] == ["itm_1", "itm_2"]
    assert [entry.item_position for entry in request.entries] == ["A-01", "A-02"]


@pytest.mark.unit
def test_parse_batch_update_item_positions_request_rejects_empty_entries():
    with pytest.raises(ValidationError):
        parse_batch_update_item_positions_request({"entries": []})


@pytest.mark.unit
def test_parse_batch_update_item_positions_request_rejects_entries_over_cap():
    with pytest.raises(ValidationError):
        parse_batch_update_item_positions_request({"entries": [_entry(i) for i in range(201)]})
