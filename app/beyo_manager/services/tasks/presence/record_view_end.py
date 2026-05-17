from datetime import datetime, timezone

from sqlalchemy import desc, select

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.services.infra.execution.db import task_db_session


async def handle_record_view_end(payload: dict, task_id: str) -> None:
    user_client_id = payload.get("user_id")
    entity_type = payload.get("entity_type")
    entity_client_id = payload.get("entity_client_id")
    if not user_client_id or not entity_type:
        return

    ended_at_raw = payload.get("ended_at")
    ended_at = (
        datetime.fromisoformat(ended_at_raw) if ended_at_raw else datetime.now(timezone.utc)
    )

    async with task_db_session() as session:
        user = (await session.execute(select(User).where(User.client_id == user_client_id))).scalar_one_or_none()
        if user is None:
            return
        result = await session.execute(
            select(UserAppViewRecord)
            .where(
                UserAppViewRecord.user_id == user.client_id,
                UserAppViewRecord.entity_type == entity_type,
                UserAppViewRecord.entity_client_id == entity_client_id,
                UserAppViewRecord.ended_at.is_(None),
            )
            .order_by(desc(UserAppViewRecord.started_at))
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return
        record.ended_at = ended_at
        await session.commit()
