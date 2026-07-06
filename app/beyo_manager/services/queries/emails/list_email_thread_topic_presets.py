from sqlalchemy import select

from beyo_manager.domain.emails.serializers import serialize_email_thread_topic_preset
from beyo_manager.models.tables.emails.email_thread_topic_preset import EmailThreadTopicPreset
from beyo_manager.services.context import ServiceContext


async def list_email_thread_topic_presets(ctx: ServiceContext) -> dict:
    result = await ctx.session.execute(
        select(EmailThreadTopicPreset)
        .where(EmailThreadTopicPreset.is_active.is_(True))
        .order_by(EmailThreadTopicPreset.sort_order.asc())
    )
    presets = result.scalars().all()
    return {
        "email_thread_topic_presets": [
            serialize_email_thread_topic_preset(item) for item in presets
        ]
    }
