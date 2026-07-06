import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.infra.email_providers.base import InboundMessage


def normalize_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    normalized = re.sub(r"^((re|fwd?|fw):\s*)+", "", subject, flags=re.IGNORECASE).strip()
    return normalized or subject.strip()


async def find_or_create_thread(
    session: AsyncSession,
    workspace_id: str,
    connection_id: str,
    inbound: InboundMessage,
) -> EmailThread:
    lookup_ids: list[str] = []
    if inbound.in_reply_to:
        lookup_ids.append(inbound.in_reply_to)
    lookup_ids.extend(inbound.references)

    for rfc_message_id in lookup_ids:
        result = await session.execute(
            select(EmailMessage).where(
                EmailMessage.rfc_message_id == rfc_message_id,
                EmailMessage.workspace_id == workspace_id,
            )
        )
        matched = result.scalar_one_or_none()
        if matched is not None:
            thread_result = await session.execute(
                select(EmailThread).where(
                    EmailThread.client_id == matched.thread_id,
                    EmailThread.workspace_id == workspace_id,
                )
            )
            thread = thread_result.scalar_one_or_none()
            if thread is not None:
                return thread

    thread = EmailThread(
        workspace_id=workspace_id,
        connection_id=connection_id,
        subject_normalized=normalize_subject(inbound.subject),
    )
    session.add(thread)
    await session.flush()
    return thread
