from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.commands.emails.requests.create_email_template_request import (
    parse_create_email_template_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit


async def create_email_template(ctx: ServiceContext) -> dict:
    request = parse_create_email_template_request(ctx.incoming_data)

    try:
        async with maybe_begin(ctx.session):
            template = EmailTemplate(
                workspace_id=ctx.workspace_id,
                name=request.name,
                subject=request.subject,
                content=request.content,
                topic=request.topic.value,
                template_type=request.template_type.value,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(template)
            await ctx.session.flush()

            await write_audit(
                session=ctx.session,
                event="email_template.created",
                workspace_id=ctx.workspace_id,
                actor_user_id=ctx.user_id,
                resource_type="email_template",
                resource_client_id=template.client_id,
                detail={"name": template.name, "topic": template.topic},
            )
    except IntegrityError as exc:
        raise ConflictError("Email template could not be created.") from exc

    return {"template": serialize_email_template(template)}
