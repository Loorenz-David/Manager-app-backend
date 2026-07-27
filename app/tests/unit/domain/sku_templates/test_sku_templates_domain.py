from datetime import datetime, timezone
from types import SimpleNamespace

from beyo_manager.domain.sku_templates.formatting import format_sku
from beyo_manager.domain.sku_templates.serializers import serialize_sku_template
from beyo_manager.domain.tasks.enums import TaskTypeEnum


def test_format_sku_zero_pads_scalar():
    assert format_sku("PRE", "-", 4, 7) == "PRE-0007"
    assert format_sku("PRE", "-", 0, 7) == "PRE-7"


def test_serialize_sku_template_calculates_next_preview():
    instance = SimpleNamespace(
        client_id="skt_1",
        workspace_id="ws_1",
        task_type=TaskTypeEnum.PRE_ORDER,
        prefix="PRE",
        separator="-",
        pad_width=4,
        last_scalar=6,
        created_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
        created_by_id="usr_1",
        updated_at=None,
        updated_by_id=None,
    )

    result = serialize_sku_template(instance)

    assert result["next_scalar"] == 7
    assert result["next_sku_preview"] == "PRE-0007"
    assert result["task_type"] == "pre_order"

