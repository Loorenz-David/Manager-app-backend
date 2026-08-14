from datetime import datetime, timezone
from pathlib import Path

import pytest

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.items.serializers import serialize_item_detail, serialize_item_list
from beyo_manager.domain.tasks.serializers import serialize_item
from beyo_manager.models.tables.items.item import Item


_MONEY_KEYS = {"item_value_minor", "item_cost_minor", "item_currency"}


def _item():
    return Item(
        client_id="itm_phase6",
        workspace_id="ws_phase6",
        article_number="A-1",
        sku="SKU-1",
        state=ItemStateEnum.PENDING,
        quantity=1,
        can_have_upholstery=True,
        created_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        created_by_id="usr_phase6",
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "endpoint_id, source_path, source_line, serializer",
    [
        ("items-list", "beyo_manager/services/queries/items/items.py", 88, lambda item: serialize_item_list(item, 0)),
        ("items-detail", "beyo_manager/services/queries/items/items.py", 144, lambda item: serialize_item_detail(item, [], None, [])),
        ("customer-detail-linked-items", "beyo_manager/domain/customers/serializers.py", 35, lambda item: serialize_item_list(item, 0)),
        ("tasks-list-tasks", "beyo_manager/services/queries/tasks/tasks.py", 388, serialize_item),
        ("tasks-get-task", "beyo_manager/services/queries/tasks/tasks.py", 697, serialize_item),
        ("task-coordination-threads", "beyo_manager/services/queries/tasks/list_task_coordination_threads.py", 224, serialize_item),
        ("upholstery-order-needs", "beyo_manager/services/queries/upholstery/upholstery_order_needs.py", 595, serialize_item),
        ("pending-seat-tasks", "beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py", 335, serialize_item),
        ("upholstery-orders", "beyo_manager/services/queries/upholstery/upholstery_orders_query.py", 496, serialize_item),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_nine_serializer_surfaces_omit_legacy_money(endpoint_id, source_path, source_line, serializer):
    del endpoint_id
    source_lines = (Path(source_path).read_text()).splitlines()
    expression = "\n".join(source_lines[source_line - 1 : source_line + 4])
    assert "serialize_item" in expression or "serialize_item_list" in expression or "serialize_item_detail" in expression
    assert all(key not in expression for key in _MONEY_KEYS)
    assert _MONEY_KEYS.isdisjoint(serializer(_item()))
