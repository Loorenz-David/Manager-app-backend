from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink


async def _create_history_record_in_session(
    session: AsyncSession,
    entity_type: HistoryRecordEntityTypeEnum,
    entity_client_id: str,
    change_type: HistoryRecordChangeTypeEnum,
    from_value: dict | None,
    to_value: dict | None,
    created_by_id: str | None,
    description: str | None = None,
    field_name: str | None = None,
    username_snapshot: str | None = None,
) -> HistoryRecord:
    now = datetime.now(timezone.utc)
    record = HistoryRecord(
        change_type=change_type,
        description=description,
        field_name=field_name,
        from_value=from_value,
        to_value=to_value,
        created_at=now,
        created_by_id=created_by_id,
        username_snapshot=username_snapshot,
    )
    session.add(record)
    await session.flush()

    link = HistoryRecordLink(
        history_record_id=record.client_id,
        entity_type=entity_type,
        entity_client_id=entity_client_id,
        created_at=now,
    )
    session.add(link)
    await session.flush()

    return record
