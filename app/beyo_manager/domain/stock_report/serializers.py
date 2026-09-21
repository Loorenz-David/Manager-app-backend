"""Response serializers for the stock-report project (master plan §6.1).

`serialize_stock_report_item` (the row's own read shape) belongs to phase 12 and is
added to this file then. The three serializers here — `serialize_stock_task_assignment`,
`serialize_item_compact`, `serialize_task_compact` — ship in phase 8 by owner ruling
(master plan §9B ruling 2): the assignment-creation response returns the same shape as
`GET /items/{client_id}/assignments` (phase 13), so a frontend can render a newly
created assignment without a second request.
"""

from beyo_manager.domain.images.serializers import serialize_image_light


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
