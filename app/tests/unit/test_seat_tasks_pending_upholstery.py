from decimal import Decimal
from types import SimpleNamespace

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.services.queries.items.seat_tasks_pending_upholstery import (
    _resolve_pending_upholstery,
)


def test_resolve_pending_upholstery_prefers_internal_selection_pending():
    upholstery = SimpleNamespace(
        client_id="iup_pending",
        source=ItemUpholsterySourceEnum.INTERNAL,
        upholstery_id=None,
        amount_meters=Decimal("2.000"),
    )

    upholstery_id, reason = _resolve_pending_upholstery([upholstery])

    assert upholstery_id == "iup_pending"
    assert reason == "missing_selection"


def test_resolve_pending_upholstery_returns_missing_selection_when_no_rows_exist():
    upholstery_id, reason = _resolve_pending_upholstery([])

    assert upholstery_id is None
    assert reason == "missing_selection"


def test_resolve_pending_upholstery_returns_missing_quantity_when_selection_exists_but_quantity_is_missing():
    upholstery = SimpleNamespace(
        client_id="iup_missing_qty",
        source=ItemUpholsterySourceEnum.INTERNAL,
        upholstery_id="uph_1",
        amount_meters=None,
    )

    upholstery_id, reason = _resolve_pending_upholstery([upholstery])

    assert upholstery_id == "iup_missing_qty"
    assert reason == "missing_quantity"
