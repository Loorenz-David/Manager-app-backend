from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select
from ulid import ULID

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.send_email_messages import SendEmailMessagesPayload
from beyo_manager.domain.emails.guards import assert_can_send_from_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.routers.utils.roles import SELLER
from beyo_manager.services.commands.emails._connection_resolver import resolve_email_connection
from beyo_manager.services.commands.emails.requests.send_email_request import SendEmailRequest
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import normalize_subject


async def send_email(ctx: ServiceContext) -> dict:
    request = SendEmailRequest.model_validate(ctx.incoming_data)
    task = None

    async with maybe_begin(ctx.session):
        thread = None
        in_reply_to = None
        references: list[str] = []
        if request.thread_client_id:
            thread_result = await ctx.session.execute(
                select(EmailThread).where(
                    EmailThread.workspace_id == ctx.workspace_id,
                    EmailThread.client_id == request.thread_client_id,
                )
            )
            thread = thread_result.scalar_one_or_none()
            if thread is None:
                raise NotFound("Email thread not found.")
            latest_message_result = await ctx.session.execute(
                select(EmailMessage)
                .where(EmailMessage.thread_id == thread.client_id)
                .order_by(EmailMessage.sent_or_received_at.desc(), EmailMessage.created_at.desc())
                .limit(1)
            )
            latest_message = latest_message_result.scalar_one_or_none()
            if latest_message and latest_message.rfc_message_id:
                in_reply_to = latest_message.rfc_message_id
                references = list(latest_message.references_json or [])
                references.append(latest_message.rfc_message_id)

        connection = await _resolve_send_connection(ctx, request, thread)
        assert_can_send_from_connection(ctx.user_id, connection.owner_user_id)

        rfc_message_id = f"<{ULID()}@{connection.smtp_host}>"
        now = datetime.now(timezone.utc)

        if thread is None:
            thread = EmailThread(
                workspace_id=ctx.workspace_id,
                connection_id=connection.client_id,
                entity_type=request.entity_type,
                entity_client_id=request.entity_client_id,
                major_entity_type=request.major_entity_type,
                major_entity_client_id=request.major_entity_client_id,
                topic=(request.topic or "")[:255] or None,
                subject_normalized=normalize_subject(request.subject),
                last_message_at=now,
            )
            ctx.session.add(thread)
            await ctx.session.flush()
        else:
            thread.last_message_at = now

        message = EmailMessage(
            workspace_id=ctx.workspace_id,
            connection_id=connection.client_id,
            thread_id=thread.client_id,
            direction=EmailMessageDirectionEnum.OUTBOUND.value,
            from_address=connection.email_address,
            from_name=connection.display_name,
            to_addresses_json=request.to_addresses,
            cc_addresses_json=request.cc_addresses,
            bcc_addresses_json=request.bcc_addresses,
            subject=request.subject,
            text_body=request.text_body,
            html_body=request.html_body,
            body_preview=(request.text_body or "")[:300] or None,
            rfc_message_id=rfc_message_id,
            in_reply_to=in_reply_to,
            references_json=references,
            sent_or_received_at=now,
            created_by_user_id=ctx.user_id,
        )
        ctx.session.add(message)
        await ctx.session.flush()

        payload = SendEmailMessagesPayload(
            workspace_id=ctx.workspace_id,
            connection_client_id=connection.client_id,
            message_ids=[message.client_id],
            request_kind="reply" if request.thread_client_id else "send",
            requested_by_user_id=ctx.user_id,
        )
        task = await create_instant_task(
            session=ctx.session,
            task_type=TaskType.SEND_EMAIL_MESSAGES,
            payload=asdict(payload),
            max_try=3,
        )

        await write_audit(
            session=ctx.session,
            event="email.reply_enqueued" if request.thread_client_id else "email.send_enqueued",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_thread",
            resource_client_id=thread.client_id,
            detail={
                "thread_client_id": thread.client_id,
                "message_client_id": message.client_id,
                "task_client_id": task.client_id,
                "to_addresses": request.to_addresses,
            },
        )

    return {
        "enqueued": True,
        "task_client_id": task.client_id if task else None,
        "thread_client_id": thread.client_id,
        "message_client_id": message.client_id,
    }


async def _resolve_send_connection(
    ctx: ServiceContext,
    request: SendEmailRequest,
    thread: EmailThread | None,
) -> EmailConnection:
    if request.connection_client_id:
        connection = await resolve_email_connection(ctx, request.connection_client_id)
    elif thread is not None and ctx.role_name != SELLER:
        connection_result = await ctx.session.execute(
            select(EmailConnection).where(
                EmailConnection.workspace_id == ctx.workspace_id,
                EmailConnection.client_id == thread.connection_id,
                EmailConnection.deleted_at.is_(None),
            )
        )
        connection = connection_result.scalar_one_or_none()
        if connection is None:
            raise NotFound("Email connection not found.")
    else:
        connection = await resolve_email_connection(ctx, None)

    if thread is not None and connection.client_id != thread.connection_id:
        raise PermissionDenied("You can only send from the email connection attached to this thread.")

    return connection
