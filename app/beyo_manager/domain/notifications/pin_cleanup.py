from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin


async def cleanup_task_pins(session: AsyncSession, task_client_id: str) -> None:
    """Delete all notification pins owned by a task graph."""
    await session.execute(
        delete(NotificationPin).where(
            NotificationPin.major_entity_type == EntityType.TASK.value,
            NotificationPin.major_client_entity_id == task_client_id,
        )
    )
