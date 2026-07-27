from sqlalchemy import select

from beyo_manager.domain.sku_templates.events import SkuTemplateEvent
from beyo_manager.domain.sku_templates.serializers import serialize_sku_template
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.services.commands.sku_templates.requests import parse_create_sku_template_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_sku_template(ctx: ServiceContext) -> dict:
    request = parse_create_sku_template_request(ctx.incoming_data)
    pending_events = []

    async with maybe_begin(ctx.session):
        existing = await ctx.session.scalar(
            select(SkuTemplate).where(
                SkuTemplate.workspace_id == ctx.workspace_id,
                SkuTemplate.task_type == request.task_type,
                SkuTemplate.is_deleted.is_(False),
            )
        )
        if existing is not None:
            raise ConflictError("A SKU template already exists for this task type.")

        sku_template = SkuTemplate(
            workspace_id=ctx.workspace_id,
            task_type=request.task_type,
            prefix=request.prefix,
            separator=request.separator,
            pad_width=request.pad_width,
            last_scalar=request.initial_scalar,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(sku_template)
        await ctx.session.flush()
        pending_events.append(
            build_workspace_event(sku_template, SkuTemplateEvent.CREATED, workspace_id=ctx.workspace_id)
        )

    await dispatch(pending_events)
    return serialize_sku_template(sku_template)

