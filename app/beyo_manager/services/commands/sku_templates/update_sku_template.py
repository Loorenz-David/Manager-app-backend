from sqlalchemy import select

from beyo_manager.domain.sku_templates.events import SkuTemplateEvent
from beyo_manager.domain.sku_templates.serializers import serialize_sku_template
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.services.commands.sku_templates.requests import parse_update_sku_template_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def update_sku_template(ctx: ServiceContext) -> dict:
    request = parse_update_sku_template_request(ctx.incoming_data)
    pending_events = []

    async with maybe_begin(ctx.session):
        sku_template = await ctx.session.scalar(
            select(SkuTemplate).where(
                SkuTemplate.workspace_id == ctx.workspace_id,
                SkuTemplate.client_id == request.client_id,
                SkuTemplate.is_deleted.is_(False),
            )
        )
        if sku_template is None:
            raise NotFound("SKU template not found.")

        fields = request.model_dump(exclude_unset=True)
        fields.pop("client_id", None)
        if "last_scalar" in fields and fields["last_scalar"] < sku_template.last_scalar:
            # Rewinding the counter would re-issue already-reserved scalars and
            # collide with existing item SKUs. Reject rather than hand out duplicates.
            raise ValidationError(
                f"last_scalar cannot be lower than the current value ({sku_template.last_scalar})."
            )
        for field in ("prefix", "separator", "pad_width", "last_scalar"):
            if field in fields:
                setattr(sku_template, field, fields[field])
        sku_template.updated_by_id = ctx.user_id
        await ctx.session.flush()
        pending_events.append(
            build_workspace_event(sku_template, SkuTemplateEvent.UPDATED, workspace_id=ctx.workspace_id)
        )

    await dispatch(pending_events)
    return serialize_sku_template(sku_template)

