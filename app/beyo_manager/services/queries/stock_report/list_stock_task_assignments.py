"""`GET /api/v1/stock-report/items/{client_id}/assignments` (master plan §6.5,
phase 13; intention §9, §9B ruling 2).

The row's non-deleted assignments in **all** states — `resolved` and
`resolved_early` included; the board's traceability surface (§14F F10) — ordered by
`created_at, client_id`. Items, tasks and images are batch-loaded once for the whole
response, and the element is built by the shipped `serialize_stock_task_assignment`,
the same function the create endpoint returns, so the two surfaces agree key for key.
"""

from __future__ import annotations

from sqlalchemy import and_, select

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_task_assignment,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task


async def list_stock_task_assignments(ctx) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    # The row lookup is the visibility boundary: absent, soft-deleted and foreign
    # are one answer, and it is `NotFound` — never an empty list.
    row = await ctx.session.scalar(
        select(StockReportItem.client_id).where(
            StockReportItem.workspace_id == ctx.workspace_id,
            StockReportItem.client_id == client_id,
            StockReportItem.is_deleted.is_(False),
        )
    )
    if row is None:
        raise NotFound("Stock report item not found.")

    assignments = (
        (
            await ctx.session.execute(
                select(StockTaskAssignment)
                .where(
                    StockTaskAssignment.workspace_id == ctx.workspace_id,
                    StockTaskAssignment.stock_report_item_id == client_id,
                    StockTaskAssignment.is_deleted.is_(False),
                )
                .order_by(
                    StockTaskAssignment.created_at.asc(),
                    StockTaskAssignment.client_id.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    if not assignments:
        return {"stock_task_assignments": []}

    item_ids = {assignment.item_id for assignment in assignments}
    task_ids = {assignment.task_id for assignment in assignments}

    items_by_id = {
        item.client_id: item
        for item in (
            await ctx.session.execute(
                select(Item).where(Item.client_id.in_(sorted(item_ids)))
            )
        )
        .scalars()
        .all()
    }
    tasks_by_id = {
        task.client_id: task
        for task in (
            await ctx.session.execute(
                select(Task).where(Task.client_id.in_(sorted(task_ids)))
            )
        )
        .scalars()
        .all()
    }

    # One image query for the whole response (the `queries/tasks/tasks.py` pattern).
    images_by_item: dict[str, list] = {}
    image_rows = await ctx.session.execute(
        select(Image, ImageLink.entity_client_id)
        .join(
            ImageLink,
            and_(
                ImageLink.image_id == Image.client_id,
                ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                ImageLink.entity_client_id.in_(sorted(item_ids)),
            ),
        )
        .where(Image.deleted_at.is_(None))
        .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
    )
    for image, item_id in image_rows.all():
        images_by_item.setdefault(item_id, []).append(image)

    return {
        "stock_task_assignments": [
            serialize_stock_task_assignment(
                assignment,
                item=items_by_id[assignment.item_id],
                task=tasks_by_id[assignment.task_id],
                images=images_by_item.get(assignment.item_id, []),
            )
            for assignment in assignments
        ]
    }
