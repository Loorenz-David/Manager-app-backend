"""Response serializers for the stock-report project (master plan §6.1).

`serialize_stock_report_item` (the row's own read shape) is phase 12's; the three
others — `serialize_stock_task_assignment`,
`serialize_item_compact`, `serialize_task_compact` — ship in phase 8 by owner ruling
(master plan §9B ruling 2): the assignment-creation response returns the same shape as
`GET /items/{client_id}/assignments` (phase 13), so a frontend can render a newly
created assignment without a second request.
"""

from beyo_manager.domain.images.serializers import serialize_image_light


def serialize_stock_report_item(row, *, category) -> dict:
    """The stock-report row's read shape (intention §9 "Response shapes"; master plan
    §6.1) — the payload of `GET /stock-report/items` and of both `PATCH` responses.

    `item_category` is **four** keys: `client_id`, `name`, `major_category` and
    `image_url` (owner addition 2026-09-21, plan 12 C4(e)). `ItemCategory.image_url`
    is nullable, and on a category with no image the key is **present and `None`,
    never absent** — an omitted key and a null key are different things to a
    renderer, and the published frontend contract states it as `string | null`.

    `category` may be a soft-deleted category: no command soft-deletes an
    `ItemCategory` today, and MC-16 says a row whose category is later deleted keeps
    working and serializes the deleted category's name — so the caller loads
    categories **by id**, never through a filtered join.

    There is no `item_type` key (intention §9: no "ItemType" concept leaks ahead of
    the Item Domain migration) and no pagination key (master plan §5: this endpoint
    is exempt from the `07_queries_local` pagination gate by ratified owner answer).
    """
    return {
        "client_id": row.client_id,
        "item_category": {
            "client_id": category.client_id,
            "name": category.name,
            "major_category": category.major_category.value,
            "image_url": category.image_url,
        },
        "properties": row.properties,
        "properties_signature": row.properties_signature,
        "quantity_requested": row.quantity_requested,
        "quantity_in_queue": row.quantity_in_queue,
        "quantity_in_progress": row.quantity_in_progress,
        "quantity_awaiting": row.quantity_awaiting,
        "priority": row.priority.value if row.priority is not None else None,
        "priority_order": row.priority_order,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "created_by_id": row.created_by_id,
        "updated_by_id": row.updated_by_id,
    }


def serialize_item_compact(item, *, images) -> dict:
    return {
        "client_id": item.client_id,
        "article_number": item.article_number,
        "sku": item.sku,
        "quantity": item.quantity,
        "item_category_snapshot": item.item_category_snapshot,
        "item_major_category_snapshot": item.item_major_category_snapshot,
        "item_images": [serialize_image_light(image) for image in images],
    }


def serialize_task_compact(task) -> dict:
    return {
        "client_id": task.client_id,
        "task_type": task.task_type.value,
        "priority": task.priority.value,
        "state": task.state.value,
        "title": task.title,
        "return_source": task.return_source.value if task.return_source else None,
        "ready_by_at": task.ready_by_at.isoformat() if task.ready_by_at else None,
        "return_method": task.return_method.value if task.return_method else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "closed_at": task.closed_at.isoformat() if task.closed_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def serialize_stock_task_assignment(assignment, *, item, task, images) -> dict:
    return {
        "client_id": assignment.client_id,
        "state": assignment.state.value,
        "stock_report_item_id": assignment.stock_report_item_id,
        "task_id": assignment.task_id,
        "item_id": assignment.item_id,
        "quantity": assignment.quantity,
        "property_mismatch_overridden": assignment.property_mismatch_overridden,
        "credited_history_record_id": assignment.credited_history_record_id,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
        "created_by_id": assignment.created_by_id,
        "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None,
        "updated_by_id": assignment.updated_by_id,
        "item": serialize_item_compact(item, images=images),
        "task": serialize_task_compact(task),
    }
