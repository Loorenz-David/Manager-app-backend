"""The three snapshot columns move together, and an empty payload is never a snapshot."""

from datetime import datetime, timedelta, timezone

import pytest

from beyo_manager.domain.items.properties_signature import compute_properties_signature
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.items._properties_snapshot import apply_properties_snapshot


def _item(**kwargs) -> Item:
    """A detached row: this helper is pure attribute work, so no session is involved."""
    item = Item(workspace_id="ws_1")
    item.properties = kwargs.get("properties")
    item.properties_signature = kwargs.get("properties_signature")
    item.properties_snapshot_at = kwargs.get("properties_snapshot_at")
    return item


def test_first_snapshot_writes_blob_signature_and_timestamp_together():
    item = _item()
    stamped = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)

    assert apply_properties_snapshot(item, {"wood": "oak"}, now=stamped) is True

    assert item.properties == {"wood": "oak"}
    assert item.properties_signature == compute_properties_signature({"wood": "oak"})
    assert item.properties_snapshot_at == stamped


def test_signature_is_derived_not_taken_from_a_caller_supplied_value():
    """A caller cannot smuggle in a signature that does not describe the blob."""
    item = _item(properties_signature="deadbeef", properties_snapshot_at=None)

    apply_properties_snapshot(item, {"wood": "walnut"})

    assert item.properties_signature == compute_properties_signature({"wood": "walnut"})
    assert item.properties_signature != "deadbeef"


@pytest.mark.parametrize("empty", [None, {}])
def test_empty_payload_never_establishes_a_snapshot(empty):
    item = _item()

    assert apply_properties_snapshot(item, empty) is False

    assert item.properties is None
    assert item.properties_signature is None
    assert item.properties_snapshot_at is None


@pytest.mark.parametrize("empty", [None, {}])
def test_empty_payload_leaves_an_existing_profile_standing(empty):
    """A frontend defaulting the field must not wipe a profile it never meant to touch."""
    established = datetime(2026, 8, 1, tzinfo=timezone.utc)
    item = _item(
        properties={"wood": "oak"},
        properties_signature=compute_properties_signature({"wood": "oak"}),
        properties_snapshot_at=established,
    )

    assert apply_properties_snapshot(item, empty) is False

    assert item.properties == {"wood": "oak"}
    assert item.properties_signature == compute_properties_signature({"wood": "oak"})
    assert item.properties_snapshot_at == established


def test_resnapshot_with_the_same_profile_does_not_bump_the_timestamp():
    """snapshot_at means "when this profile was established", not "when ingestion last spoke"."""
    established = datetime(2026, 8, 1, tzinfo=timezone.utc)
    item = _item(
        properties={"wood": "oak", "legs": 4},
        properties_signature=compute_properties_signature({"wood": "oak", "legs": 4}),
        properties_snapshot_at=established,
    )

    # Same profile, different key order — the signature canonicalizes it away.
    assert apply_properties_snapshot(item, {"legs": 4, "wood": "oak"}, now=established + timedelta(days=5)) is False

    assert item.properties_snapshot_at == established


def test_a_changed_profile_rewrites_all_three_columns():
    established = datetime(2026, 8, 1, tzinfo=timezone.utc)
    later = datetime(2026, 8, 29, tzinfo=timezone.utc)
    item = _item(
        properties={"wood": "oak"},
        properties_signature=compute_properties_signature({"wood": "oak"}),
        properties_snapshot_at=established,
    )

    assert apply_properties_snapshot(item, {"wood": "oak", "carving": "heavy"}, now=later) is True

    assert item.properties == {"wood": "oak", "carving": "heavy"}
    assert item.properties_signature == compute_properties_signature({"wood": "oak", "carving": "heavy"})
    assert item.properties_snapshot_at == later


def test_a_stored_signature_with_no_timestamp_is_repaired_rather_than_trusted():
    """Half-written state must not make a real snapshot look like a no-op."""
    item = _item(
        properties=None,
        properties_signature=compute_properties_signature({"wood": "oak"}),
        properties_snapshot_at=None,
    )

    assert apply_properties_snapshot(item, {"wood": "oak"}) is True

    assert item.properties == {"wood": "oak"}
    assert item.properties_snapshot_at is not None


@pytest.mark.parametrize("bad", ["wood=oak", ["wood", "oak"], 5, True])
def test_non_object_payloads_are_rejected_as_validation_errors(bad):
    item = _item()

    with pytest.raises(ValidationError):
        apply_properties_snapshot(item, bad)

    assert item.properties is None
    assert item.properties_signature is None
