import logging
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.domain.emails.arrival_notifications import (
    emit_arrival_realtime_events,
    enqueue_arrival_notifications,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.services.infra.email_providers.message_processor import process_inbound_messages
from beyo_manager.services.infra.email_providers.registry import get_email_provider

logger = logging.getLogger(__name__)


async def handle_email_inbox_sync(payload: dict, task_client_id: str) -> None:
    now = datetime.now(timezone.utc)
    connection_id = payload.get("connection_client_id")
    workspace_id = payload.get("workspace_id")
    realtime_events = []
    logger.info(
        "email_inbox_sync_start | task_id=%s connection_id=%s workspace_id=%s",
        task_client_id, connection_id, workspace_id,
    )

    async for session in get_db_session():
        async with session.begin():
            connection_result = await session.execute(
                select(EmailConnection).where(
                    EmailConnection.client_id == connection_id,
                    EmailConnection.workspace_id == workspace_id,
                    EmailConnection.deleted_at.is_(None),
                )
            )
            connection = connection_result.scalar_one_or_none()
            if connection is None:
                logger.warning(
                    "email_inbox_sync | missing_connection | task_id=%s connection_id=%s",
                    task_client_id, connection_id,
                )
                return

            sync_state_result = await session.execute(
                select(EmailSyncState).where(EmailSyncState.connection_id == connection.client_id)
            )
            sync_state = sync_state_result.scalar_one_or_none()
            if sync_state is None:
                logger.warning(
                    "email_inbox_sync | missing_sync_state | task_id=%s connection_id=%s",
                    task_client_id, connection_id,
                )
                return

            logger.info(
                "email_inbox_sync | calling_provider | task_id=%s folder=%s last_seen_uid=%s",
                task_client_id, sync_state.folder, sync_state.last_seen_uid,
            )
            provider = get_email_provider(connection)
            sync_result = await provider.sync_inbox(
                folder=sync_state.folder,
                uidvalidity=sync_state.uidvalidity,
                last_seen_uid=sync_state.last_seen_uid,
            )
            if not sync_result.success:
                sync_state.last_error = sync_result.error
                sync_state.last_sync_at = now
                if sync_result.error and "auth" in sync_result.error.lower():
                    connection.status = EmailConnectionStatusEnum.AUTH_FAILED.value
                logger.warning(
                    "email_inbox_sync | sync_failed | task_id=%s error=%r",
                    task_client_id, sync_result.error,
                )
                return

            logger.info(
                "email_inbox_sync | provider_ok | task_id=%s new_messages=%d new_last_seen_uid=%s",
                task_client_id, len(sync_result.new_messages), sync_result.new_last_seen_uid,
            )

            process_result = await process_inbound_messages(
                session=session,
                workspace_id=workspace_id,
                connection=connection,
                inbound_messages=sync_result.new_messages,
            )
            realtime_events = await enqueue_arrival_notifications(
                session=session,
                workspace_id=workspace_id,
                connection=connection,
                process_result=process_result,
            )

            sync_state.last_seen_uid = sync_result.new_last_seen_uid
            sync_state.uidvalidity = sync_result.new_uidvalidity
            sync_state.last_sync_at = now
            sync_state.last_successful_sync_at = now
            sync_state.last_error = None
            logger.info(
                "email_inbox_sync_done | task_id=%s saved=%d new_last_seen_uid=%s",
                task_client_id, process_result.saved_count, sync_result.new_last_seen_uid,
            )
        break

    await emit_arrival_realtime_events(realtime_events)
