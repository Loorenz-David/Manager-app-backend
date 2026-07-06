from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit


async def delete_email_template(ctx: ServiceContext) -> dict:
    template_client_id = str(ctx.incoming_data.get("template_client_id") or "").strip()
    if not template_client_id:
        raise NotFound("Email template not found.")

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(EmailTemplate).where(
                EmailTemplate.workspace_id == ctx.workspace_id,
                EmailTemplate.client_id == template_client_id,
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise NotFound("Email template not found.")

        await write_audit(
            session=ctx.session,
            event="email_template.deleted",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_template",
            resource_client_id=template.client_id,
            detail={"name": template.name, "topic": template.topic},
        )
        await ctx.session.delete(template)

    return {}
