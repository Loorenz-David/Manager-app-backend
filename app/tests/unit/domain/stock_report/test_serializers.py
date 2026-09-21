"""Master plan §6.1, §9B response shapes; plan 8 §6 C4(l) (the fourteen-key shape).

Unit-tier: every ORM instance here is constructed but never flushed (charter rule 3
still holds — these are real model instances, never hand-built dicts).
"""

from datetime import datetime, timezone

import pytest

from beyo_manager.domain.images.enums import ImageStorageProviderEnum, ImageSourceTypeEnum
from beyo_manager.domain.stock_report.serializers import (
    serialize_item_compact,
    serialize_stock_task_assignment,
    serialize_task_compact,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum
from beyo_manager.domain.tasks.enums import TaskPriorityEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task

pytestmark = pytest.mark.unit

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

_ITEM_COMPACT_KEYS = {
    "client_id",
    "article_number",
    "sku",
    "quantity",
    "item_category_snapshot",
    "item_major_category_snapshot",
    "item_images",
}
_TASK_COMPACT_KEYS = {
    "client_id",
    "task_type",
    "priority",
    "state",
    "title",
    "return_source",
    "ready_by_at",
    "return_method",
    "created_at",
    "updated_at",
    "closed_at",
    "completed_at",
}
_ASSIGNMENT_KEYS = {
    "client_id",
    "state",
    "stock_report_item_id",
    "task_id",
    "item_id",
    "quantity",
    "property_mismatch_overridden",
    "credited_history_record_id",
    "created_at",
    "created_by_id",
    "updated_at",
    "updated_by_id",
    "item",
    "task",
}


def _item():
    return Item(
        client_id="itm_test",
        workspace_id="ws_test",
        article_number="SR-1",
        sku="sku-1",
        quantity=4,
        item_category_snapshot="Dining Chairs",
        item_major_category_snapshot="seat",
    )


def _task():
    return Task(
        client_id="tsk_test",
        workspace_id="ws_test",
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        priority=TaskPriorityEnum.NORMAL,
        state=TaskStateEnum.PENDING,
        title="A task",
        created_at=NOW,
    )


def _assignment():
    return StockTaskAssignment(
        client_id="sta_test",
        workspace_id="ws_test",
        stock_report_item_id="sri_test",
        task_id="tsk_test",
        item_id="itm_test",
        quantity=4,
        property_mismatch_overridden=False,
        state=StockTaskAssignmentStateEnum.IN_QUEUE,
        created_at=NOW,
        created_by_id="usr_test",
    )


def _image():
    return Image(
        client_id="img_test",
        image_url="https://example.com/photo.png",
        storage_provider=ImageStorageProviderEnum.S3,
        source_type=ImageSourceTypeEnum.UPLOADED,
        width_px=100,
        height_px=100,
        file_size_bytes=1234,
    )


def test_serialize_item_compact_returns_exact_key_set_and_images():
    result = serialize_item_compact(_item(), images=[_image()])
    assert set(result) == _ITEM_COMPACT_KEYS
    assert result["client_id"] == "itm_test"
    assert result["quantity"] == 4
    assert len(result["item_images"]) == 1
    assert result["item_images"][0]["client_id"] == "img_test"


def test_serialize_item_compact_empty_images_is_empty_list():
    result = serialize_item_compact(_item(), images=[])
    assert result["item_images"] == []


def test_serialize_task_compact_returns_exact_key_set_and_enum_values():
    result = serialize_task_compact(_task())
    assert set(result) == _TASK_COMPACT_KEYS
    assert result["task_type"] == "internal"
    assert result["priority"] == "normal"
    assert result["state"] == "pending"
    assert result["return_source"] is None
    assert result["return_method"] is None
    assert result["created_at"] == NOW.isoformat()


def test_serialize_stock_task_assignment_returns_the_fourteen_keys_with_nested_item_and_task():
    result = serialize_stock_task_assignment(
        _assignment(), item=_item(), task=_task(), images=[]
    )
    assert set(result) == _ASSIGNMENT_KEYS
    assert len(_ASSIGNMENT_KEYS) == 14
    assert result["state"] == "in_queue"
    assert result["item"] == serialize_item_compact(_item(), images=[])
    assert result["task"] == serialize_task_compact(_task())
