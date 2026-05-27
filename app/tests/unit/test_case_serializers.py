from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.cases.serializers import serialize_case, serialize_case_list_item


@pytest.mark.unit
def test_serialize_case_returns_case_type_object():
    conversation = SimpleNamespace(
        client_id="ccv_1",
        messages_count=3,
        last_message_seq=7,
        created_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )
    case_type = SimpleNamespace(
        name="broken tool",
        image_url="https://cdn.example.com/case-types/broken-tool.webp",
    )
    case = SimpleNamespace(
        client_id="ca_1",
        state="open",
        participants_count=2,
        conversations_count=1,
        messages_count=3,
        created_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
        created_by_id="usr_1",
        conversations=[conversation],
        case_type=case_type,
    )

    serialized = serialize_case(case)

    assert serialized["case_type"] == {
        "name": "broken tool",
        "image": "https://cdn.example.com/case-types/broken-tool.webp",
    }
    assert "type_label" not in serialized


@pytest.mark.unit
def test_serialize_case_list_item_returns_case_type_object():
    case_type = SimpleNamespace(
        name="out of upholstery",
        image_url=None,
    )
    created_by = SimpleNamespace(
        client_id="usr_2",
        username="admin",
        profile_picture=None,
    )
    case = SimpleNamespace(
        client_id="ca_2",
        created_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
        state="resolving",
        case_type_id="cty_1",
        participants_count=1,
        messages_count=5,
        case_type=case_type,
    )

    serialized = serialize_case_list_item(
        case,
        created_by=created_by,
        entity_type="task",
        last_message_seq=12,
    )

    assert serialized["case_type_id"] == "cty_1"
    assert serialized["case_type"] == {"name": "out of upholstery", "image": None}
    assert "type_label" not in serialized