from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.sku_templates.formatting import format_sku
from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate


async def allocate_sku_scalar_in_session(
    session: AsyncSession,
    *,
    workspace_id: str,
    task_type: TaskTypeEnum,
    user_id: str | None,
) -> tuple[str, str, int]:
    """Atomically increment a SKU template's counter and format the resulting SKU.

    Must run inside the caller's own transaction (maybe_begin block) so the
    increment rolls back together with the row it's being allocated for —
    this is what keeps the sequence gapless across failed creates.

    Returns (sku, sku_template_client_id, reserved_scalar).
    """
    stmt = (
        update(SkuTemplate)
        .where(
            SkuTemplate.workspace_id == workspace_id,
            SkuTemplate.task_type == task_type,
            SkuTemplate.is_deleted.is_(False),
        )
        .values(last_scalar=SkuTemplate.last_scalar + 1, updated_by_id=user_id)
        .returning(
            SkuTemplate.client_id,
            SkuTemplate.last_scalar,
            SkuTemplate.prefix,
            SkuTemplate.separator,
            SkuTemplate.pad_width,
        )
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        raise NotFound("SKU template not found.")

    sku = format_sku(row.prefix, row.separator, row.pad_width, row.last_scalar)
    return sku, row.client_id, row.last_scalar
