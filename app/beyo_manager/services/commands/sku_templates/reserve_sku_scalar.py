from sqlalchemy import update

from beyo_manager.domain.sku_templates.events import SkuTemplateEvent
from beyo_manager.domain.sku_templates.formatting import format_sku
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.services.commands.sku_templates.requests import parse_sku_template_task_type
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def reserve_sku_scalar(ctx: ServiceContext) -> dict:
    task_type = parse_sku_template_task_type(ctx.incoming_data)
    pending_events = []

    async with maybe_begin(ctx.session):
        stmt = (
            update(SkuTemplate)
            .where(
                SkuTemplate.workspace_id == ctx.workspace_id,
                SkuTemplate.task_type == task_type,
                SkuTemplate.is_deleted.is_(False),
            )
            .values(last_scalar=SkuTemplate.last_scalar + 1, updated_by_id=ctx.user_id)
            .returning(
                SkuTemplate.client_id,
                SkuTemplate.last_scalar,
                SkuTemplate.prefix,
                SkuTemplate.separator,
                SkuTemplate.pad_width,
            )
        )
        row = (await ctx.session.execute(stmt)).one_or_none()
        if row is None:
            raise NotFound("SKU template not found.")

        reserved_scalar = row.last_scalar
        sku = format_sku(row.prefix, row.separator, row.pad_width, reserved_scalar)
        pending_events.append(
            WorkspaceEvent(
                event_name=SkuTemplateEvent.SCALAR_RESERVED,
                client_id=row.client_id,
                workspace_id=ctx.workspace_id,
                extra={"last_scalar": reserved_scalar},
            )
        )

    await dispatch(pending_events)
    return {
        "client_id": row.client_id,
        "task_type": task_type.value,
        "reserved_scalar": reserved_scalar,
        "sku": sku,
    }

