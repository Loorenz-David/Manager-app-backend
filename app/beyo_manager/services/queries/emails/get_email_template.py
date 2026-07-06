from sqlalchemy import select

from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.context import ServiceContext


async def get_email_template(ctx: ServiceContext) -> dict:
    template_client_id = str(ctx.incoming_data.get("template_client_id") or "").strip()

    result = await ctx.session.execute(
        select(EmailTemplate).where(
            EmailTemplate.workspace_id == ctx.workspace_id,
            EmailTemplate.client_id == template_client_id,
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise NotFound("Email template not found.")

    return {"template": serialize_email_template(template)}
