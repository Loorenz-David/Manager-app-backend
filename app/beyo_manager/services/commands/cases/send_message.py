import logging
from dataclasses import asdict

from sqlalchemy import select

from beyo_manager.domain.cases.events import CaseEvent, ConversationMessageEvent, conversation_message_extra
from beyo_manager.domain.cases.serializers import serialize_message
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.notifications.enums import NotificationType
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.commands.cases.requests import parse_send_message_request
from beyo_manager.services.commands.cases.message_writes import write_case_message
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_conversation_event, build_user_event
from beyo_manager.services.infra.execution.task_factory import create_instant_task

logger = logging.getLogger(__name__)


async def send_message(ctx: ServiceContext) -> dict:
    request = parse_send_message_request(ctx.incoming_data or {})

    async with ctx.session.begin():
        conversation = await ctx.session.get(CaseConversation, request.conversation_client_id)
        if conversation is None:
            raise NotFound("Conversation not found")
        logger.info(
            "[send_message] writing message | conversation=%s case=%s sender=%s",
            conversation.client_id,
            conversation.case_id,
            ctx.user_id,
        )
        message, seq = await write_case_message(
            ctx,
            conversation=conversation,
            client_id=request.client_id,
            content=request.content,
            plain_text=request.plain_text,
        )
        case_client_id = conversation.case_id
        conversation_client_id = conversation.client_id
        case_type_label = await ctx.session.scalar(
            select(Case.type_label).where(Case.client_id == case_client_id)
        )

        participant_result = await ctx.session.execute(
            select(CaseParticipant.user_id, CaseParticipant.last_read_message_seq).where(
                CaseParticipant.case_id == case_client_id,
                CaseParticipant.user_id != ctx.user_id,
            )
        )
        other_participants = participant_result.all()
        notify_ids = [row.user_id for row in other_participants]
        # per-user unread counts for the realtime UserEvent
        unread_by_user = {
            row.user_id: max(seq - (row.last_read_message_seq or 0), 0)
            for row in other_participants
        }
        logger.info(
            "[send_message] other participants | conversation=%s notify_ids=%s unread_by_user=%s",
            conversation_client_id,
            notify_ids,
            unread_by_user,
        )
        if notify_ids:
            sender_name = ctx.identity.get("username") or "someone"
            title = (
                f"Message from {sender_name} for {case_type_label}"
                if case_type_label
                else f"Message from {sender_name}"
            )
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(
                    NotificationPayload(
                        notification_type=NotificationType.CASE_MESSAGE,
                        user_ids=notify_ids,
                        title=title,
                        body=(request.plain_text or "")[:80],
                        entity_type="case",
                        entity_client_id=case_client_id,
                        exclude_viewing=[{"entity_type": "case", "entity_client_id": case_client_id}],
                    )
                ),
            )
    event = build_conversation_event(
        message,
        ConversationMessageEvent.CREATED,
        conversation_id=conversation_client_id,
        workspace_id=ctx.workspace_id,
        extra=conversation_message_extra(seq),
    )
    logger.info(
        "[send_message] dispatching ConversationRoomEvent | event=%s conversation=%s message=%s",
        event.event_name,
        conversation_client_id,
        message.client_id,
    )
    events = [event]
    for user_id, unread_count in unread_by_user.items():
        events.append(
            build_user_event(
                user_id=user_id,
                event_name=CaseEvent.UNREAD_UPDATED,
                client_id=case_client_id,
                extra={"unread_count": unread_count},
            )
        )
    logger.info(
        "[send_message] dispatching %d events (1 ConversationRoomEvent + %d UserEvents) | message=%s",
        len(events),
        len(unread_by_user),
        message.client_id,
    )
    await dispatch(events)
    logger.info("[send_message] dispatch complete | message=%s", message.client_id)
    return {"message": serialize_message(message)}
