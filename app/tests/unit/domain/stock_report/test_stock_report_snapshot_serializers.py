"""The three snapshot-layer shapes (2026-09-26; draft versions 2026-09-28): the row
with its `snapshot`, the item snapshot, the version. Pure ORM instances, no session."""

from datetime import datetime, timezone

import pytest

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_item,
    serialize_stock_report_item_snapshot,
    serialize_stock_report_snapshot_version,
)
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)

ROW_KEYS = {
    "client_id",
    "item_category",
    "properties",
    "properties_signature",
    "quantity_requested",
    "quantity_in_queue",
    "quantity_in_progress",
    "quantity_awaiting",
    "created_at",
    "updated_at",
    "created_by_id",
    "updated_by_id",
    "snapshot",
}
SNAPSHOT_KEYS = {
    "client_id",
    "version_id",
    "stock_report_item_id",
    "quantity_requested",
    "quantity_requested_scanner",
    "quantity_requested_source",
    "quantity_in_queue",
    "quantity_in_progress",
    "quantity_awaiting",
    "quantity_missing",
    "quantity_missing_source",
    "active_quantity_missing",
    "quantity_resolved",
    "priority",
    "priority_order",
    "active_at",
    "closed_at",
    "created_at",
    "updated_at",
    "updated_by_id",
}
VERSION_KEYS = {
    "client_id",
    "state",
    "title",
    "active_at",
    "closed_at",
    "scheduled_activation_at",
    "scheduled_activation_keeps_active_missing",
    "snapshot_count",
    "created_at",
    "created_by_id",
    "closed_by_id",
}


def _row():
    return StockReportItem(
        client_id="sri_test",
        workspace_id="ws_test",
        item_category_id="itc_test",
        properties={"wood_group": ["teak"]},
        properties_signature="sig",
        quantity_requested=12,
        quantity_in_queue=3,
        quantity_in_progress=2,
        quantity_awaiting=1,
        created_at=NOW,
    )


def _category():
    return ItemCategory(
        client_id="itc_test",
        workspace_id="ws_test",
        name="Dining Chairs",
        major_category=ItemMajorCategoryEnum.SEAT,
    )


def _snapshot(*, closed_at=None, active_at=NOW, scanner=5, manual=None, missing=1):
    return StockReportItemSnapshot(
        client_id="srs_test",
        workspace_id="ws_test",
        version_id="srv_test",
        stock_report_item_id="sri_test",
        quantity_requested_scanner=scanner,
        quantity_requested_manual=manual,
        quantity_in_queue=9,
        quantity_in_progress=9,
        quantity_awaiting=9,
        quantity_missing=missing,
        quantity_resolved=0,
        priority=StockReportPriorityEnum.HIGH,
        priority_order=2,
        active_at=active_at,
        closed_at=closed_at,
        created_at=NOW,
    )


def _draft_snapshot(*, manual=None, missing=None):
    return _snapshot(active_at=None, scanner=None, manual=manual, missing=missing)


def _version(**overrides):
    values = dict(
        client_id="srv_test",
        workspace_id="ws_test",
        title=None,
        active_at=NOW,
        closed_at=None,
        scheduled_activation_at=None,
        scheduled_activation_keeps_active_missing=False,
        snapshot_count=7,
        created_at=NOW,
        created_by_id="usr_test",
    )
    values.update(overrides)
    return StockReportSnapshotVersion(**values)


def test_row_has_no_priority_keys_and_embeds_its_snapshot():
    payload = serialize_stock_report_item(_row(), category=_category(), snapshot=_snapshot())
    assert set(payload) == ROW_KEYS
    assert "priority" not in payload and "priority_order" not in payload
    assert payload["quantity_requested"] == 12
    assert set(payload["snapshot"]) == SNAPSHOT_KEYS
    assert payload["snapshot"]["stock_report_item_id"] == "sri_test"


def test_row_snapshot_is_null_when_there_is_none():
    payload = serialize_stock_report_item(_row(), category=_category(), snapshot=None)
    assert payload["snapshot"] is None


def test_active_snapshot_reads_the_rows_live_counters_and_its_own_frozen_demand():
    payload = serialize_stock_report_item_snapshot(_snapshot(), row=_row())
    assert payload["closed_at"] is None
    assert payload["quantity_requested"] == 5  # frozen, not the row's 12
    assert payload["quantity_requested_scanner"] == 5
    assert payload["quantity_requested_source"] == "scanner"
    assert (
        payload["quantity_in_queue"],
        payload["quantity_in_progress"],
        payload["quantity_awaiting"],
    ) == (3, 2, 1)  # the row's, not the stored 9s
    assert payload["priority"] == "high"
    assert payload["priority_order"] == 2
    assert payload["quantity_missing"] == 1
    assert payload["quantity_missing_source"] == "own"
    # On the active snapshot itself the borrowed value is its own number, whatever
    # the caller threaded through.
    assert payload["active_quantity_missing"] == 1
    assert payload["quantity_resolved"] == 0
    assert payload["active_at"] == NOW.isoformat()


def test_awaiting_on_the_wire_keeps_the_units_scanner_resolved():
    """Owner ruling (addendum 2026-09-26): completion never drops because Scanner
    processed a shelf. The row's awaiting fell when they resolved; the snapshot
    remembers them in `quantity_resolved`, and the wire `quantity_awaiting` is the
    sum — while active (row's live awaiting) and once closed (frozen awaiting)."""
    snapshot = _snapshot()
    snapshot.quantity_resolved = 4
    active = serialize_stock_report_item_snapshot(snapshot, row=_row())
    assert active["quantity_awaiting"] == 1 + 4
    assert active["quantity_resolved"] == 4
    # The other two counters are untouched by resolution.
    assert (active["quantity_in_queue"], active["quantity_in_progress"]) == (3, 2)

    closed = _snapshot(closed_at=LATER)
    closed.quantity_resolved = 4
    frozen = serialize_stock_report_item_snapshot(closed, row=_row())
    assert frozen["quantity_awaiting"] == 9 + 4


def test_closed_snapshot_reads_its_own_frozen_counters():
    payload = serialize_stock_report_item_snapshot(_snapshot(closed_at=LATER), row=_row())
    assert payload["closed_at"] == LATER.isoformat()
    assert (
        payload["quantity_in_queue"],
        payload["quantity_in_progress"],
        payload["quantity_awaiting"],
    ) == (9, 9, 9)
    # A closed version's rows show today's active value, threaded by the caller.
    assert payload["active_quantity_missing"] is None
    assert (
        serialize_stock_report_item_snapshot(
            _snapshot(closed_at=LATER), row=_row(), active_quantity_missing=6
        )["active_quantity_missing"]
        == 6
    )


def test_unprioritised_snapshot_serializes_both_nulls():
    snapshot = _snapshot()
    snapshot.priority = None
    snapshot.priority_order = None
    payload = serialize_stock_report_item_snapshot(snapshot, row=_row())
    assert payload["priority"] is None
    assert payload["priority_order"] is None


# ---------------------------------------------------------------------------
# Draft versions (2026-09-28): the six computed keys
# ---------------------------------------------------------------------------


def test_a_draft_snapshot_is_live_and_borrows_the_active_missing():
    payload = serialize_stock_report_item_snapshot(
        _draft_snapshot(), row=_row(), active_quantity_missing=5
    )
    assert payload["active_at"] is None
    assert payload["quantity_requested"] == 12  # the live row
    assert payload["quantity_requested_scanner"] == 12
    assert payload["quantity_requested_source"] == "scanner"
    assert payload["quantity_missing"] == 5
    assert payload["quantity_missing_source"] == "active"
    assert payload["active_quantity_missing"] == 5
    # Live counters, as any open snapshot.
    assert (payload["quantity_in_queue"], payload["quantity_awaiting"]) == (3, 1)


def test_a_draft_with_a_manual_value_shows_it_and_scanner_beside_it():
    payload = serialize_stock_report_item_snapshot(
        _draft_snapshot(manual=7), row=_row(), active_quantity_missing=5
    )
    assert payload["quantity_requested"] == 7
    assert payload["quantity_requested_scanner"] == 12
    assert payload["quantity_requested_source"] == "manual"


def test_a_draft_with_a_typed_missing_shows_its_own_and_the_boards_beside_it():
    payload = serialize_stock_report_item_snapshot(
        _draft_snapshot(missing=2), row=_row(), active_quantity_missing=5
    )
    assert payload["quantity_missing"] == 2
    assert payload["quantity_missing_source"] == "own"
    assert payload["active_quantity_missing"] == 5


def test_a_draft_with_no_active_version_reads_zero_with_source_none():
    payload = serialize_stock_report_item_snapshot(_draft_snapshot(), row=_row())
    assert payload["quantity_missing"] == 0
    assert payload["quantity_missing_source"] == "none"
    assert payload["active_quantity_missing"] is None


def test_an_activated_snapshot_with_an_override_keeps_it_over_the_frozen_value():
    payload = serialize_stock_report_item_snapshot(
        _snapshot(scanner=12, manual=7), row=_row()
    )
    assert payload["quantity_requested"] == 7
    assert payload["quantity_requested_scanner"] == 12
    assert payload["quantity_requested_source"] == "manual"


def test_version_shape():
    payload = serialize_stock_report_snapshot_version(_version())
    assert set(payload) == VERSION_KEYS
    assert payload["state"] == "active"
    assert payload["title"] is None
    assert payload["closed_at"] is None
    assert payload["closed_by_id"] is None
    assert payload["scheduled_activation_at"] is None
    assert payload["scheduled_activation_keeps_active_missing"] is False
    assert payload["snapshot_count"] == 7
    assert payload["active_at"] == NOW.isoformat()


def test_version_state_and_schedule_on_the_wire():
    draft = serialize_stock_report_snapshot_version(
        _version(
            active_at=None,
            title="  Upholstery push  ",
            scheduled_activation_at=LATER,
            scheduled_activation_keeps_active_missing=True,
        )
    )
    assert draft["state"] == "draft"
    assert draft["active_at"] is None
    assert draft["scheduled_activation_at"] == LATER.isoformat()
    assert draft["scheduled_activation_keeps_active_missing"] is True
    # The serializer echoes the column; trimming is the command's job.
    assert draft["title"] == "  Upholstery push  "
    closed = serialize_stock_report_snapshot_version(_version(closed_at=LATER))
    assert closed["state"] == "closed"
