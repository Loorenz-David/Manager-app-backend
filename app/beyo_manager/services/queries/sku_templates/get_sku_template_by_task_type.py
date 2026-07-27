from sqlalchemy import select

from beyo_manager.domain.sku_templates.serializers import serialize_sku_template
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.services.commands.sku_templates.requests import parse_sku_template_task_type
from beyo_manager.services.context import ServiceContext


async def get_sku_template_by_task_type(ctx: ServiceContext) -> dict:
    task_type = parse_sku_template_task_type(ctx.incoming_data)
    sku_template = await ctx.session.scalar(
        select(SkuTemplate).where(
            SkuTemplate.workspace_id == ctx.workspace_id,
            SkuTemplate.task_type == task_type,
            SkuTemplate.is_deleted.is_(False),
        )
    )
    if sku_template is None:
        raise NotFound("SKU template not found.")
    return serialize_sku_template(sku_template)

