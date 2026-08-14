import pytest
from sqlalchemy import text


@pytest.mark.integration
async def test_process_item_cost_result_enum_member_is_present(db_session) -> None:
    value = await db_session.scalar(
        text(
            "SELECT enumlabel FROM pg_enum "
            "WHERE enumtypid = 'task_type_enum'::regtype "
            "AND enumlabel = 'process_item_cost_result'"
        )
    )

    assert value == "process_item_cost_result"
