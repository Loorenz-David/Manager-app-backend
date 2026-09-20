import pytest

from beyo_manager.services.commands.stock_report._repair_records import _text


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, "true"), (False, "false"), (None, None), (4, "4")],
)
def test_repair_record_values_are_contract_text(value, expected):
    assert _text(value) == expected
