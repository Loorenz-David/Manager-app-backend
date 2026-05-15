from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum, InputContentTypeEnum
from beyo_manager.domain.content.schemas import InputContentBlock
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.content.content_mention import ContentMention
from beyo_manager.models.tables.content.content_mention_link import ContentMentionLink


def validate_content_block(block: dict) -> InputContentBlock:
    if not isinstance(block, dict):
        raise ValidationError("Each content block must be a dict")

    block_type = block.get("type")
    if not block_type:
        raise ValidationError("Content block missing 'type'")

    try:
        type_enum = InputContentTypeEnum(block_type)
    except ValueError as exc:
        raise ValidationError(f"Invalid content block type: {block_type!r}") from exc

    text = block.get("text")
    if text is None:
        raise ValidationError("Content block missing 'text'")

    mention = None
    if type_enum == InputContentTypeEnum.MENTION:
        mention = block.get("mention")
        if not isinstance(mention, dict):
            raise ValidationError("MENTION block requires a 'mention' object")
        for key in ("mention_table", "mention_id", "client_id"):
            if key not in mention:
                raise ValidationError(f"MENTION block missing '{key}' in mention dict")

    label_value = None
    if type_enum == InputContentTypeEnum.LABEL:
        label_value = block.get("label_value")
        if label_value is None:
            raise ValidationError("LABEL block missing 'label_value'")

    link = None
    if type_enum == InputContentTypeEnum.LINK:
        link = block.get("link")
        if link is None:
            raise ValidationError("LINK block missing 'link'")

    return InputContentBlock(
        type=type_enum.value,
        text=text,
        mention=mention,
        label_value=label_value,
        link=link,
    )


def validate_content(content) -> list[InputContentBlock]:
    if not isinstance(content, list):
        raise ValidationError("content must be a list of blocks")
    return [validate_content_block(block) for block in content]


async def process_content_mentions(
    session: AsyncSession,
    content: list,
    entity_type: ContentMentionLinkEntityTypeEnum,
    entity_client_id: str,
    created_by_id: str,
    replace: bool = False,
) -> None:
    if replace:
        await session.execute(
            delete(ContentMentionLink).where(
                ContentMentionLink.entity_type == entity_type,
                ContentMentionLink.entity_client_id == entity_client_id,
            )
        )
        await session.flush()

    for block in content or []:
        if block.get("type") != InputContentTypeEnum.MENTION.value:
            continue
        mention_data = block.get("mention") or {}
        mention_table = mention_data.get("mention_table")
        mention_client_id = mention_data.get("client_id")
        if not mention_table or not mention_client_id:
            continue

        result = await session.execute(
            select(ContentMention).where(
                ContentMention.mention_table == mention_table,
                ContentMention.mention_id == mention_client_id,
            )
        )
        mention = result.scalar_one_or_none()
        if mention is None:
            mention = ContentMention(mention_table=mention_table, mention_id=mention_client_id)
            session.add(mention)
            await session.flush()

        existing = await session.execute(
            select(ContentMentionLink).where(
                ContentMentionLink.content_mention_id == mention.client_id,
                ContentMentionLink.entity_type == entity_type,
                ContentMentionLink.entity_client_id == entity_client_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(ContentMentionLink(
                content_mention_id=mention.client_id,
                entity_type=entity_type,
                entity_client_id=entity_client_id,
                created_by_id=created_by_id,
            ))
