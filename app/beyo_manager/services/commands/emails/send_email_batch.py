from dataclasses import asdict
from datetime import datetime, timezone

from ulid import ULID

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.domain.emails.guards import assert_can_send_from_connection
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.send_email_messages import SendEmailMessagesPayload
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.commands.emails._connection_resolver import resolve_email_connection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.commands.emails.requests.send_email_batch_request import (
    BatchEmailTarget,
    SendEmailBatchRequest,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import normalize_subject


async def send_email_batch(ctx: ServiceContext) -> dict:
    request = SendEmailBatchRequest.model_validate(ctx.incoming_data)
    task = None

    async with maybe_begin(ctx.session):
        connection = await resolve_email_connection(ctx, request.connection_client_id)
        assert_can_send_from_connection(ctx.user_id, connection.owner_user_id)

        now = datetime.now(timezone.utc)
        rows: list[dict] = []

        for target in request.targets:
            thread, message = _build_target_records(
                ctx=ctx,
                connection=connection,
                request=request,
                target=target,
                now=now,
            )
            ctx.session.add(thread)
            await ctx.session.flush()
            message.thread_id = thread.client_id
            ctx.session.add(message)
            await ctx.session.flush()

            rows.append(
                {
                    "thread": thread,
                    "message": message,
                    "to_addresses": target.to_addresses,
                }
            )

        task = await create_instant_task(
            session=ctx.session,
            task_type=TaskType.SEND_EMAIL_MESSAGES,
            payload=asdict(
                SendEmailMessagesPayload(
                    workspace_id=ctx.workspace_id,
                    connection_client_id=connection.client_id,
                    message_ids=[row["message"].client_id for row in rows],
                    request_kind="batch_send",
                    requested_by_user_id=ctx.user_id,
                )
            ),
            max_try=3,
        )

        await write_audit(
            session=ctx.session,
            event="email.batch_send_enqueued",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=connection.client_id,
            detail={
                "target_count": len(request.targets),
                "queued_count": len(rows),
                "connection_id": connection.client_id,
                "task_client_id": task.client_id,
            },
        )

    return {
        "enqueued": True,
        "task_client_id": task.client_id if task else None,
        "target_count": len(request.targets),
        "queued_count": len(rows),
        "results": [
            {
                "thread_client_id": row["thread"].client_id,
                "message_client_id": row["message"].client_id,
                "to_addresses": row["to_addresses"],
            }
            for row in rows
        ],
    }


def _build_target_records(
    ctx: ServiceContext,
    connection: EmailConnection,
    request: SendEmailBatchRequest,
    target: BatchEmailTarget,
    now: datetime,
) -> tuple[EmailThread, EmailMessage]:
    rfc_message_id = f"<{ULID()}@{connection.smtp_host}>"
    thread = EmailThread(
        workspace_id=ctx.workspace_id,
        connection_id=connection.client_id,
        entity_type=target.entity_type,
        entity_client_id=target.entity_client_id,
        major_entity_type=target.major_entity_type,
        major_entity_client_id=target.major_entity_client_id,
        topic=(target.topic or "")[:255] or None,
        subject_normalized=normalize_subject(request.subject),
        last_message_at=now,
    )

    message = EmailMessage(
        workspace_id=ctx.workspace_id,
        connection_id=connection.client_id,
        thread_id="",
        direction=EmailMessageDirectionEnum.OUTBOUND.value,
        from_address=connection.email_address,
        from_name=connection.display_name,
        to_addresses_json=target.to_addresses,
        cc_addresses_json=request.cc_addresses,
        bcc_addresses_json=request.bcc_addresses,
        subject=request.subject,
        text_body=request.text_body,
        html_body=request.html_body,
        body_preview=(request.text_body or "")[:300] or None,
        rfc_message_id=rfc_message_id,
        in_reply_to=None,
        references_json=[],
        sent_or_received_at=now,
        created_by_user_id=ctx.user_id,
    )

    return thread, message
