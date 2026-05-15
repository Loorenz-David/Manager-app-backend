from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.services.infra.execution.db import task_db_session


async def handle_record_view_start(payload: dict, task_id: str) -> None:
    user_client_id = payload.get("user_id")
    entity_type = payload.get("entity_type")
    entity_client_id = payload.get("entity_client_id")
    if not user_client_id or not entity_type:
        return
    async with task_db_session() as session:
        user = (await session.execute(select(User).where(User.client_id == user_client_id))).scalar_one_or_none()
        if user is None:
            return

        now = datetime.now(timezone.utc)
        debounce_cutoff = now - timedelta(seconds=settings.presence_debounce_seconds)
        existing = (await session.execute(
            select(UserAppViewRecord).where(
                UserAppViewRecord.user_id == user.client_id,
                UserAppViewRecord.entity_type == entity_type,
                UserAppViewRecord.entity_client_id == entity_client_id,
                UserAppViewRecord.ended_at.is_(None),
                UserAppViewRecord.started_at >= debounce_cutoff,
            ).limit(1)
        )).scalar_one_or_none()
        if existing is not None:
            return  # within debounce window — extend the existing record silently

        record = UserAppViewRecord(
            user_id=user.client_id,
            entity_type=entity_type,
            entity_client_id=entity_client_id,
            started_at=now,
        )
        session.add(record)
        await session.flush()
        user.last_app_view_record_id = record.client_id
        await session.commit()
