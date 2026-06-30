from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.cases.serializers import serialize_case, serialize_case_conversation_message
from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image
from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation_message import CaseConversationMessage
from beyo_manager.models.tables.content.content_mention import ContentMention
from beyo_manager.models.tables.content.content_mention_link import ContentMentionLink
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext


async def get_case(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    before_message_seq = data.get("before_message_seq")
    limit = int(data.get("messages_limit") or 10)
    limit = max(1, min(limit, 50))

    case = await ctx.session.get(
        Case,
        data.get("case_client_id"),
        options=[
            selectinload(Case.conversations),
            selectinload(Case.created_by),
            selectinload(Case.case_type),
        ],
    )
    if case is None:
        raise NotFound("Case not found")

    conversation = (getattr(case, "conversations", []) or [None])[0]
    if conversation is None:
        return {
            "case": serialize_case(case, case_type=case.__dict__.get("case_type")),
            "case_conversation_messages": [],
            "messages_pagination": {
                "limit": limit,
                "has_more": False,
                "next_before_message_seq": None,
            },
        }

    messages_stmt = (
        select(CaseConversationMessage)
        .options(selectinload(CaseConversationMessage.created_by))
        .where(CaseConversationMessage.case_conversation_id == conversation.client_id)
    )
    if before_message_seq is not None:
        messages_stmt = messages_stmt.where(CaseConversationMessage.message_seq < int(before_message_seq))
    messages_stmt = messages_stmt.order_by(CaseConversationMessage.message_seq.desc()).limit(limit + 1)

    messages_desc = (await ctx.session.execute(messages_stmt)).scalars().all()
    has_more = len(messages_desc) > limit
    if has_more:
        messages_desc = messages_desc[:limit]

    message_ids = [message.client_id for message in messages_desc]
    images_by_message: dict[str, list[dict]] = {message_id: [] for message_id in message_ids}
    mentions_by_message: dict[str, list[dict]] = {message_id: [] for message_id in message_ids}
    if message_ids:
        image_links = (
            await ctx.session.execute(
                select(ImageLink)
                .options(
                    selectinload(ImageLink.image).selectinload(Image.last_event),
                    selectinload(ImageLink.image).selectinload(Image.image_annotations),
                )
                .where(
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.CASE_CONVERSATION_MESSAGE,
                    ImageLink.entity_client_id.in_(message_ids),
                )
                .order_by(ImageLink.entity_client_id.asc(), ImageLink.display_order.asc(), ImageLink.created_at.asc())
            )
        ).scalars().all()
        for image_link in image_links:
            if image_link.image is not None:
                images_by_message.setdefault(image_link.entity_client_id, []).append(
                    serialize_image(image_link.image, include_annotations=True)
                )

        mention_rows = await ctx.session.execute(
            select(ContentMentionLink, ContentMention)
            .join(ContentMention, ContentMention.client_id == ContentMentionLink.content_mention_id)
            .where(
                ContentMentionLink.entity_type == ContentMentionLinkEntityTypeEnum.CASE_CONVERSATION_MESSAGE,
                ContentMentionLink.entity_client_id.in_(message_ids),
            )
            .order_by(ContentMentionLink.entity_client_id.asc(), ContentMention.client_id.asc())
        )
        mention_rows = mention_rows.all()

        user_ids = sorted(
            {
                mention.mention_id
                for _, mention in mention_rows
                if mention.mention_table == "users" and mention.mention_id
            }
        )
        users_by_id: dict[str, User] = {}
        if user_ids:
            users = (await ctx.session.execute(select(User).where(User.client_id.in_(user_ids)))).scalars().all()
            users_by_id = {user.client_id: user for user in users}

        for mention_link, mention in mention_rows:
            mention_data = None
            if mention.mention_table == "users":
                user = users_by_id.get(mention.mention_id)
                mention_data = serialize_user_working_section_member(user) if user is not None else None
            mentions_by_message.setdefault(mention_link.entity_client_id, []).append(
                {
                    "mention_table": mention.mention_table,
                    "mention_id": mention.mention_id,
                    "mention_data": mention_data,
                }
            )

    # Keep messages in ascending sequence so the latest message appears last in the returned page.
    messages_asc = list(reversed(messages_desc))
    serialized_messages = [
        serialize_case_conversation_message(
            message,
            case_id=case.client_id,
            created_by=getattr(message, "created_by", None),
            images=images_by_message.get(message.client_id, []),
            mentions=mentions_by_message.get(message.client_id, []),
        )
        for message in messages_asc
    ]

    case_mentions_map: dict[tuple[str, str], dict] = {}
    for message_mentions in mentions_by_message.values():
        for mention in message_mentions:
            key = (mention["mention_table"], mention["mention_id"])
            case_mentions_map[key] = mention
    case_payload = serialize_case(case, case_type=case.__dict__.get("case_type"))
    case_payload["mentions"] = list(case_mentions_map.values())

    next_before_message_seq = messages_desc[-1].message_seq if has_more and messages_desc else None
    return {
        "case": case_payload,
        "case_conversation_messages": serialized_messages,
        "messages_pagination": {
            "limit": limit,
            "has_more": has_more,
            "next_before_message_seq": next_before_message_seq,
        },
    }
