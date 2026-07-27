from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate


_SKU_TEMPLATES = (
    (TaskTypeEnum.PRE_ORDER, "PRE_ORDER", "-", 0, 0),
)


async def seed_sku_templates(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    sku_template_ids: dict[str, str] = {}
    for task_type, prefix, separator, pad_width, initial_scalar in _SKU_TEMPLATES:
        existing = await session.scalar(
            select(SkuTemplate).where(
                SkuTemplate.workspace_id == workspace_id,
                SkuTemplate.task_type == task_type,
                SkuTemplate.is_deleted.is_(False),
            )
        )
        if existing is not None:
            sku_template_ids[task_type.value] = existing.client_id
            continue

        sku_template = SkuTemplate(
            workspace_id=workspace_id,
            task_type=task_type,
            prefix=prefix,
            separator=separator,
            pad_width=pad_width,
            last_scalar=initial_scalar,
            created_by_id=None,
        )
        session.add(sku_template)
        await session.flush()
        sku_template_ids[task_type.value] = sku_template.client_id

    return sku_template_ids
