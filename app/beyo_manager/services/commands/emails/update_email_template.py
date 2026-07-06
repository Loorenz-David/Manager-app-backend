from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.commands.emails.requests.update_email_template_request import (
    parse_update_email_template_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit


async def update_email_template(ctx: ServiceContext) -> dict:
    request = parse_update_email_template_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(EmailTemplate).where(
                EmailTemplate.workspace_id == ctx.workspace_id,
                EmailTemplate.client_id == request.template_client_id,
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise NotFound("Email template not found.")

        if request.name is not None:
            template.name = request.name
        if request.subject is not None:
            template.subject = request.subject
        if request.content is not None:
            template.content = request.content
        if request.topic is not None:
            template.topic = request.topic.value
        if request.template_type is not None:
            template.template_type = request.template_type.value
        template.updated_by_id = ctx.user_id
        template.updated_at = datetime.now(timezone.utc)

        await write_audit(
            session=ctx.session,
            event="email_template.updated",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_template",
            resource_client_id=template.client_id,
            detail={"name": template.name, "topic": template.topic},
        )

    return {"template": serialize_email_template(template)}
