from dataclasses import asdict

from sqlalchemy import func, select, text, update

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseLinkRoleEnum, CaseStateEnum
from beyo_manager.domain.cases.events import CaseEvent, ConversationMessageEvent, conversation_message_extra
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.notifications.enums import NotificationType
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.models.tables.cases.case_type import CaseType
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.cases.requests import parse_create_case_request
from beyo_manager.services.commands.cases.message_writes import write_case_message
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import (
    build_conversation_event,
    build_user_event,
    build_workspace_event,
)
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def create_case(ctx: ServiceContext) -> dict:
    request = parse_create_case_request(ctx.incoming_data or {})
    case_type_id = request.case_type_id
    type_label = request.type_label
    entity_type_value = request.entity_type
    entity_client_id = request.entity_client_id
    participant_ids = list(dict.fromkeys(request.participants or []))
    skip_participant_ids = list(dict.fromkeys(request.skip_participants or []))
    case_type = None
    initial_message = None
    initial_message_seq = None

    if bool(entity_type_value) != bool(entity_client_id):
        raise ValidationError("entity_type and entity_client_id must be provided together.")

    link_entity_type: CaseLinkEntityTypeEnum | None = None
    if entity_type_value is not None:
        try:
            link_entity_type = CaseLinkEntityTypeEnum(entity_type_value)
        except ValueError as exc:
            allowed = ", ".join(value.value for value in CaseLinkEntityTypeEnum)
            raise ValidationError(f"Invalid entity_type '{entity_type_value}'. Allowed values: {allowed}") from exc

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "ca")

    async with ctx.session.begin():
        case_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(Case, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            case_kwargs["client_id"] = request.client_id

        if case_type_id:
            case_type = await ctx.session.get(CaseType, case_type_id)
            if case_type and type_label is None:
                type_label = case_type.name
        await ctx.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('cases_scalar_id'))")
        )
        scalar_id_result = await ctx.session.execute(
            select(func.coalesce(func.max(Case.scalar_id), 0) + 1)
        )
        case_scalar_id = scalar_id_result.scalar_one()
        ref_index = entity_client_id.split("-", 1)[0] if entity_client_id else "N"
        reference_number = f"{ref_index}-{str(case_scalar_id).zfill(4)}"
        case = Case(
            **case_kwargs,
            created_by_id=ctx.user_id,
            updated_by_id=ctx.user_id,
            state=CaseStateEnum.OPEN,
            case_type_id=case_type_id,
            type_label=type_label,
            scalar_id=case_scalar_id,
            reference_number=reference_number,
        )
        ctx.session.add(case)
        await ctx.session.flush()

        conversation = CaseConversation(
            case=case,
            created_by_id=ctx.user_id,
            state=CaseStateEnum.OPEN,
        )
        ctx.session.add(conversation)
        case.conversations_count = 1

        if link_entity_type is not None and entity_client_id is not None:
            ctx.session.add(
                CaseLink(
                    case_id=case.client_id,
                    entity_type=link_entity_type,
                    entity_client_id=entity_client_id,
                    role=CaseLinkRoleEnum.SUBJECT,
                )
            )

        if request.selected_all is True:
            memberships_stmt = (
                select(WorkspaceMembership.user_id)
                .where(
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.is_active.is_(True),
                    WorkspaceMembership.user_id != ctx.user_id,
                )
                .order_by(WorkspaceMembership.user_id.asc())
            )
            if skip_participant_ids:
                memberships_stmt = memberships_stmt.where(
                    WorkspaceMembership.user_id.notin_(skip_participant_ids)
                )
            memberships_result = await ctx.session.execute(memberships_stmt)
            participant_ids = memberships_result.scalars().all()

        # The creator is always a participant in the newly created case.
        participant_ids = list(dict.fromkeys([ctx.user_id, *(participant_ids or [])]))

        if participant_ids:
            participants = [
                CaseParticipant(case_id=case.client_id, user_id=user_id)
                for user_id in participant_ids
            ]
            if participants:
                ctx.session.add_all(participants)
                case.participants_count = len(participants)
        if request.initial_message is not None:
            initial_message, initial_message_seq = await write_case_message(
                ctx,
                conversation=conversation,
                client_id=request.initial_message.client_id,
                content=request.initial_message.content,
                plain_text=request.initial_message.plain_text,
            )
            await ctx.session.execute(
                update(CaseParticipant)
                .where(
                    CaseParticipant.case_id == case.client_id,
                    CaseParticipant.user_id == ctx.user_id,
                )
                .values(
                    last_read_message_seq=func.greatest(
                        CaseParticipant.last_read_message_seq,
                        initial_message_seq,
                    )
                )
            )

        notify_ids = [user_id for user_id in participant_ids if user_id != ctx.user_id]
        if notify_ids:
            if initial_message is not None:
                notif_type = NotificationType.CASE_MESSAGE
                notif_title = "New case"
                notif_body = (request.initial_message.plain_text or "")[:80]
            else:
                notif_type = NotificationType.CASE_PARTICIPANT_ADDED
                notif_title = "You've been added to a case"
                notif_body = "A new case was created and you are a participant."
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(
                    NotificationPayload(
                        notification_type=notif_type,
                        user_ids=notify_ids,
                        title=notif_title,
                        body=notif_body,
                        entity_type="case",
                        entity_client_id=case.client_id,
                        exclude_viewing=[{"entity_type": "case", "entity_client_id": case.client_id}],
                    )
                ),
            )
    event = build_workspace_event(case, CaseEvent.CREATED, workspace_id=ctx.workspace_id)
    events = [event]
    if initial_message is not None and initial_message_seq is not None:
        events.append(
            build_conversation_event(
                initial_message,
                ConversationMessageEvent.CREATED,
                conversation_id=conversation.client_id,
                workspace_id=ctx.workspace_id,
                extra=conversation_message_extra(initial_message_seq),
            )
        )
    has_initial_message = initial_message is not None
    for user_id in participant_ids:
        unread_count = 1 if has_initial_message and user_id != ctx.user_id else 0
        events.append(
            build_user_event(
                user_id=user_id,
                event_name=CaseEvent.PARTICIPANT_ADDED,
                client_id=case.client_id,
                extra={"unread_count": unread_count},
            )
        )
    await dispatch(events)
    return {"case_client_id": case.client_id}
