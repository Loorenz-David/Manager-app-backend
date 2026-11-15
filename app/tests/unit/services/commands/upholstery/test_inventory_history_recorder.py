from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum as S
from beyo_manager.domain.upholstery.enums import InventoryMovementTriggerEnum, InventoryMovementTypeEnum
from beyo_manager.domain.upholstery.serializers import serialize_inventory_history_record
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.upholstery._inventory_history import (
    BucketSnapshot,
    InventoryMovementContext,
    RequirementStateTracker,
    allocation_details,
    correlation_id_for,
    reset_movement_scope,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import _reduce_need
from beyo_manager.services.queries.upholstery.get_upholstery_inventory_history import (
    _chain_break,
    decode_cursor,
    encode_cursor,
)


def _session():
    return SimpleNamespace(info={})


def _ctx(user_id="", username=""):
    return SimpleNamespace(user_id=user_id, username=username, session=_session())


def test_from_service_never_writes_empty_actor():
    m = InventoryMovementContext.from_service(_ctx(), InventoryMovementTriggerEnum.MANUAL_STORED_SET)
    assert m.actor_id is None and m.username_snapshot is None
    m = InventoryMovementContext.from_service(_ctx("usr_1", "ann"), InventoryMovementTriggerEnum.ORDER_CREATED)
    assert (m.actor_id, m.username_snapshot) == ("usr_1", "ann")


def test_correlation_is_stable_within_scope_and_resets():
    session = _session()
    first = correlation_id_for(session)
    assert correlation_id_for(session) == first
    reset_movement_scope(session)
    assert correlation_id_for(session) != first


def test_for_requirement_takes_current_state_as_from_state():
    m = InventoryMovementContext.system(_session(), InventoryMovementTriggerEnum.TASK_DELETED, task_id="tsk_1")
    req = SimpleNamespace(client_id="iur_1", item_upholstery_id="iup_1", state=S.ORDERED)
    scoped = m.for_requirement(req, to_state=S.FAILED)
    assert (scoped.requirement_id, scoped.item_upholstery_id, scoped.from_state, scoped.to_state, scoped.task_id) == (
        "iur_1",
        "iup_1",
        S.ORDERED,
        S.FAILED,
        "tsk_1",
    )


def test_bucket_snapshot_treats_null_as_zero():
    inv = SimpleNamespace(
        current_stored_amount_meters=None,
        current_amount_in_use_meters=Decimal("1"),
        current_amount_in_need_meters=None,
        current_amount_ordered_meters=Decimal("2"),
        total_upholstery_used_meters=None,
        total_upholstery_used_inventory_meters=None,
        total_upholstery_used_surplus_meters=None,
        total_upholstery_surplus_meters=None,
    )
    snap = BucketSnapshot.of(inv)
    assert snap.stored == Decimal("0") and snap.in_use == Decimal("1") and snap.ordered == Decimal("2")


def test_reduce_need_reports_clamp():
    assert _reduce_need(Decimal("5"), Decimal("2")) == (Decimal("3"), False)
    assert _reduce_need(Decimal("1"), Decimal("2")) == (Decimal("0"), True)
    assert _reduce_need(None, Decimal("0")) == (Decimal("0"), False)


def test_tracker_diffs_only_captured_requirements():
    a = SimpleNamespace(client_id="a", state=S.NEEDS_ORDERING)
    b = SimpleNamespace(client_id="b", state=S.NEEDS_ORDERING)
    late = SimpleNamespace(client_id="late", state=S.NEEDS_ORDERING)
    tracker = RequirementStateTracker.capture([a, b])
    a.state = S.ORDERED
    tracker.add([late, a])  # a keeps its first-captured state
    late.state = S.AVAILABLE
    ghost = SimpleNamespace(client_id="ghost", state=S.AVAILABLE)
    transitions = tracker.transitions([a, b, late, ghost, a])
    assert [(t.requirement.client_id, t.from_state, t.to_state) for t in transitions] == [
        ("a", S.NEEDS_ORDERING, S.ORDERED),
        ("late", S.NEEDS_ORDERING, S.AVAILABLE),
    ]


def test_allocation_details_caps_ids_and_stringifies_pool():
    reqs = [SimpleNamespace(client_id=f"r{i}") for i in range(60)]
    details = allocation_details(pool_meters=Decimal("1.500"), resolved=reqs, target_state=S.AVAILABLE)
    assert details["resolved_count"] == 60
    assert len(details["resolved_requirement_ids"]) == 50
    assert details["pool_meters"] == "1.500"
    assert details["target_state"] == "available"


def test_cursor_round_trip_and_rejects_garbage():
    at = datetime(2026, 11, 15, 12, 30, tzinfo=timezone.utc)
    assert decode_cursor(encode_cursor(at, "uih_X")) == (at, "uih_X")
    with pytest.raises(ValidationError):
        decode_cursor("!!!")


def _rec(**kw):
    base = {f"{p}_{b}_meters": None for p in ("before", "after") for b in (
        "stored", "in_use", "in_need", "ordered", "total_used", "total_used_inventory",
        "total_used_surplus", "total_surplus")}
    base.update(
        client_id="uih_1",
        movement_type=InventoryMovementTypeEnum.ORDER_RECEIVED,
        trigger="order_received",
        created_at=datetime(2026, 11, 15, tzinfo=timezone.utc),
        is_reconstructed=False,
        created_by_id=None,
        username_snapshot=None,
        quantity_meters=Decimal("2.000"),
        requirement_id=None,
        requirement_from_state=None,
        requirement_to_state=None,
        item_id=None,
        upholstery_order_id=None,
        anomaly=None,
        note=None,
        details=None,
        previous_record_id=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_chain_break_compares_before_with_previous_after():
    prev = _rec(after_stored_meters=Decimal("3"), after_ordered_meters=Decimal("1"))
    continues = _rec(before_stored_meters=Decimal("3"), before_ordered_meters=Decimal("1"))
    jumps = _rec(before_stored_meters=Decimal("5"), before_ordered_meters=Decimal("1"))
    assert _chain_break(continues, prev) is False
    assert _chain_break(jumps, prev) is True
    assert _chain_break(jumps, None) is False
    assert _chain_break(_rec(), prev) is False  # no before-snapshot (reconstructed / creation)


def test_serializer_computes_delta_and_handles_missing_snapshots():
    rec = _rec(
        before_stored_meters=Decimal("1.000"), after_stored_meters=Decimal("3.000"),
        before_ordered_meters=Decimal("2.000"), after_ordered_meters=Decimal("0.000"),
    )
    out = serialize_inventory_history_record(
        rec, users={}, tasks={}, items={}, orders={}, task_id=None, task_resolution=None, children=[]
    )
    assert out["delta"]["stored"] == "2.000"
    assert out["delta"]["ordered"] == "-2.000"
    assert out["created_by"] is None
    assert out["task"] is None and out["task_resolution"] is None
    assert out["children"] == []

    bare = serialize_inventory_history_record(
        _rec(is_reconstructed=True), users={}, tasks={}, items={}, orders={}, task_id=None, task_resolution=None
    )
    assert bare["before"] is None and bare["after"] is None and bare["delta"] is None
    assert "children" not in bare
