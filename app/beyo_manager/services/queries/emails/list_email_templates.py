from sqlalchemy import select

from beyo_manager.domain.emails.enums import EmailTemplateTopicEnum
from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _parse_topics(raw_topics: str | None) -> list[str]:
    if raw_topics is None:
        return []

    normalized_topics: list[str] = []
    allowed_topics = {item.value for item in EmailTemplateTopicEnum}
    for raw_part in raw_topics.split(","):
        topic = raw_part.strip().lower()
        if not topic:
            continue
        if topic not in allowed_topics:
            raise ValidationError(f"topic: Unsupported value '{topic}'.")
        normalized_topics.append(topic)
    return normalized_topics


async def list_email_templates(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    topics = _parse_topics(ctx.query_params.get("topic"))

    stmt = (
        select(EmailTemplate)
        .where(EmailTemplate.workspace_id == ctx.workspace_id)
        .order_by(EmailTemplate.created_at.desc(), EmailTemplate.client_id.desc())
    )
    if topics:
        stmt = stmt.where(EmailTemplate.topic.in_(topics))

    result = await ctx.session.execute(stmt.offset(offset).limit(limit + 1))
    rows = result.scalars().all()
    page = rows[:limit]

    return {
        "templates_pagination": {
            "items": [serialize_email_template(item) for item in page],
            "has_more": len(rows) > limit,
            "limit": limit,
            "offset": offset,
        }
    }
