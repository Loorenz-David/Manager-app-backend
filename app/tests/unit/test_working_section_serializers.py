from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.working_sections.serializers import (
    serialize_working_section_compact,
    serialize_working_section_member,
)


@pytest.mark.unit
def test_serialize_working_section_member_includes_working_section_id():
    row = SimpleNamespace(
        membership_id="wsme_1",
        working_section_id="wse_1",
        user_id="usr_1",
        username="manager",
        assigned_at=datetime.now(timezone.utc),
    )

    result = serialize_working_section_member(row)

    assert result["membership_id"] == "wsme_1"
    assert result["working_section_id"] == "wse_1"
    assert result["user_id"] == "usr_1"


@pytest.mark.unit
def test_serialize_working_section_compact_includes_allows_batch_working():
    result = serialize_working_section_compact(
        client_id="wse_1",
        name="Ground oil",
        image="https://example.com/ground-oil.webp",
        order_list=2,
        allows_batch_working=True,
    )

    assert result["client_id"] == "wse_1"
    assert result["allows_batch_working"] is True
