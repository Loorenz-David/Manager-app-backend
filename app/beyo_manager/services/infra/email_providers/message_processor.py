from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.services.infra.email_providers.base import InboundMessage
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import find_or_create_thread

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    saved_count: int = 0
    skipped_count: int = 0
    new_thread_ids: set[str] = field(default_factory=set)
    created_messages: list[EmailMessage] = field(default_factory=list)


async def process_inbound_messages(
    session: AsyncSession,
    workspace_id: str,
    connection: EmailConnection,
    inbound_messages: list[InboundMessage],
) -> ProcessResult:
    now = datetime.now(timezone.utc)
    result = ProcessResult()

    for inbound in inbound_messages:
        duplicate_result = await session.execute(
            select(EmailMessage).where(
                EmailMessage.connection_id == connection.client_id,
                EmailMessage.provider_folder == inbound.provider_folder,
                EmailMessage.provider_uid == str(inbound.provider_uid),
            )
        )
        if duplicate_result.scalar_one_or_none() is not None:
            logger.debug("message_processor | duplicate_skipped | uid=%s", inbound.provider_uid)
            result.skipped_count += 1
            continue

        thread = await find_or_create_thread(
            session=session,
            workspace_id=workspace_id,
            connection_id=connection.client_id,
            inbound=inbound,
        )
        message = EmailMessage(
            workspace_id=workspace_id,
            connection_id=connection.client_id,
            thread_id=thread.client_id,
            direction=EmailMessageDirectionEnum.INBOUND.value,
            provider_folder=inbound.provider_folder,
            provider_uid=str(inbound.provider_uid),
            from_address=inbound.from_address,
            from_name=inbound.from_name,
            to_addresses_json=inbound.to_addresses,
            cc_addresses_json=inbound.cc_addresses,
            subject=inbound.subject,
            text_body=inbound.text_body,
            text_body_clean=inbound.text_body_clean,
            html_body=inbound.html_body,
            body_preview=inbound.body_preview,
            rfc_message_id=inbound.rfc_message_id,
            in_reply_to=inbound.in_reply_to,
            references_json=inbound.references,
            raw_headers_json=inbound.raw_headers,
            sent_or_received_at=inbound.received_at,
        )
        session.add(message)
        await session.flush()
        thread.last_message_at = inbound.received_at or now
        thread.last_inbound_message_at = inbound.received_at or now
        result.saved_count += 1
        result.new_thread_ids.add(thread.client_id)
        result.created_messages.append(message)
        logger.info(
            "message_processor | message_saved | uid=%s subject=%r from=%r in_reply_to=%r thread_id=%s",
            inbound.provider_uid, inbound.subject, inbound.from_address,
            inbound.in_reply_to, thread.client_id,
        )

    return result
