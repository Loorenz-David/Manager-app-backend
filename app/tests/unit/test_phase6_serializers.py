from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.items.serializers import serialize_item_detail, serialize_item_list
from beyo_manager.domain.tasks.serializers import serialize_item


_MONEY_KEYS = {"item_value_minor", "item_cost_minor", "item_currency"}


def _item():
    return SimpleNamespace(
        client_id="itm_phase6",
        workspace_id="ws_phase6",
        article_number="A-1",
        sku="SKU-1",
        state=SimpleNamespace(value="pending"),
        item_category_id=None,
        item_category_snapshot=None,
        item_major_category_snapshot=None,
        quantity=1,
        designer=None,
        height_in_cm=None,
        width_in_cm=None,
        depth_in_cm=None,
        item_position=None,
        item_zone=None,
        external_id=None,
        external_url=None,
        external_source=None,
        external_order_id=None,
        can_have_upholstery=True,
        created_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        created_by_id="usr_phase6",
        updated_at=None,
        updated_by_id=None,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "endpoint_id, serializer",
    [
        ("items-list", lambda item: serialize_item_list(item, 0)),
        ("items-detail", lambda item: serialize_item_detail(item, [], None, [])),
        ("customer-detail-linked-items", lambda item: serialize_item_list(item, 0)),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_items_serializer_surfaces_omit_legacy_money(endpoint_id, serializer):
    assert _MONEY_KEYS.isdisjoint(serializer(_item()))


@pytest.mark.unit
@pytest.mark.parametrize(
    "endpoint_id",
    [
        "tasks-list-tasks",
        "tasks-get-task",
        "task-coordination-threads",
        "pending-seat-tasks",
        "upholstery-orders",
        "upholstery-order-needs",
    ],
)
def test_tasks_serializer_surfaces_omit_legacy_money(endpoint_id):
    assert _MONEY_KEYS.isdisjoint(serialize_item(_item()))
