from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.domain.execution.payloads.send_email_messages import SendEmailMessagesPayload
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.email_providers.base import OutboundMessage
from beyo_manager.services.infra.email_providers.registry import get_email_provider
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_user_event

logger = logging.getLogger(__name__)


async def handle_send_email_messages(raw: dict, task_client_id: str) -> None:
    payload = SendEmailMessagesPayload(**raw)

    provider = None
    outbound_messages: list[OutboundMessage] = []
    message_ids: list[str] = []

    async for session in get_db_session():
        connection_result = await session.execute(
            select(EmailConnection).where(
                EmailConnection.client_id == payload.connection_client_id,
                EmailConnection.workspace_id == payload.workspace_id,
                EmailConnection.deleted_at.is_(None),
            )
        )
        connection = connection_result.scalar_one_or_none()
        if connection is None:
            logger.warning(
                "send_email_messages | missing_connection | task_id=%s connection_id=%s",
                task_client_id,
                payload.connection_client_id,
            )
            return

        message_result = await session.execute(
            select(EmailMessage)
            .where(
                EmailMessage.workspace_id == payload.workspace_id,
                EmailMessage.client_id.in_(payload.message_ids),
                EmailMessage.direction == EmailMessageDirectionEnum.OUTBOUND.value,
                EmailMessage.send_attempted_at.is_(None),
            )
            .order_by(EmailMessage.created_at.asc())
        )
        messages = list(message_result.scalars().all())
        if not messages:
            logger.info("send_email_messages | nothing_pending | task_id=%s", task_client_id)
            return

        provider = get_email_provider(connection)
        outbound_messages = [
            OutboundMessage(
                from_address=message.from_address,
                from_name=message.from_name,
                to_addresses=list(message.to_addresses_json or []),
                cc_addresses=list(message.cc_addresses_json or []),
                bcc_addresses=list(message.bcc_addresses_json or []),
                subject=message.subject or "",
                text_body=message.text_body,
                html_body=message.html_body,
                rfc_message_id=message.rfc_message_id or "",
                in_reply_to=message.in_reply_to,
                references=list(message.references_json or []),
            )
            for message in messages
        ]
        message_ids = [message.client_id for message in messages]
        break

    if provider is None or not outbound_messages:
        return

    batch_result = await provider.send_email_batch(outbound_messages)
    now = datetime.now(timezone.utc)
    result_by_message_id = {
        message_id: send_result
        for message_id, send_result in zip(message_ids, batch_result.results, strict=True)
    }

    async for session in get_db_session():
        async with session.begin():
            message_result = await session.execute(
                select(EmailMessage).where(
                    EmailMessage.workspace_id == payload.workspace_id,
                    EmailMessage.client_id.in_(message_ids),
                )
            )
            messages = list(message_result.scalars().all())
            attempted_count = 0
            sent_count = 0
            failed_count = 0
            for message in messages:
                if message.send_attempted_at is not None:
                    continue
                send_result = result_by_message_id.get(message.client_id)
                if send_result is None:
                    continue
                message.send_attempted_at = now
                message.send_error = send_result.error
                attempted_count += 1
                if send_result.success:
                    sent_count += 1
                else:
                    failed_count += 1

            await write_audit(
                session=session,
                event="email.delivery_completed",
                workspace_id=payload.workspace_id,
                actor_user_id=payload.requested_by_user_id,
                resource_type="email_connection",
                resource_client_id=payload.connection_client_id,
                detail={
                    "task_client_id": task_client_id,
                    "request_kind": payload.request_kind,
                    "attempted_count": attempted_count,
                    "sent_count": sent_count,
                    "failed_count": failed_count,
                    "message_ids": message_ids,
                },
            )

        if payload.requested_by_user_id:
            await event_bus.dispatch(
                [
                    build_user_event(
                        user_id=payload.requested_by_user_id,
                        event_name="email_batch:delivery_completed",
                        client_id=task_client_id,
                        extra={
                            "request_kind": payload.request_kind,
                            "connection_client_id": payload.connection_client_id,
                            "attempted_count": attempted_count,
                            "sent_count": sent_count,
                            "failed_count": failed_count,
                            "message_ids": message_ids,
                        },
                    )
                ]
            )

        logger.info(
            "send_email_messages_done | task_id=%s request_kind=%s attempted=%d sent=%d failed=%d",
            task_client_id,
            payload.request_kind,
            attempted_count,
            sent_count,
            failed_count,
        )
        return
