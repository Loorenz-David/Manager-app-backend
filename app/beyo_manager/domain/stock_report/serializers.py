"""Response serializers for the stock-report project (master plan §6.1).

`serialize_stock_report_item` (the row's own read shape) is phase 12's; the three
others — `serialize_stock_task_assignment`,
`serialize_item_compact`, `serialize_task_compact` — ship in phase 8 by owner ruling
(master plan §9B ruling 2): the assignment-creation response returns the same shape as
`GET /items/{client_id}/assignments` (phase 13), so a frontend can render a newly
created assignment without a second request.
"""

from beyo_manager.domain.images.serializers import serialize_image_light


def serialize_stock_report_item(row, *, category, snapshot) -> dict:
    """The stock-report row's read shape (intention §9 "Response shapes"; master plan
    §6.1) — the payload of `GET /stock-report/items` and of the `PATCH` responses.

    `item_category` is **four** keys: `client_id`, `name`, `major_category` and
    `image_url` (owner addition 2026-09-21, plan 12 C4(e)). `ItemCategory.image_url`
    is nullable, and on a category with no image the key is **present and `None`,
    never absent** — an omitted key and a null key are different things to a
    renderer, and the published frontend contract states it as `string | null`.

    `category` may be a soft-deleted category: no command soft-deletes an
    `ItemCategory` today, and MC-16 says a row whose category is later deleted keeps
    working and serializes the deleted category's name — so the caller loads
    categories **by id**, never through a filtered join.

    `snapshot` is the row's active `StockReportItemSnapshot`, or `None` on a live read
    (`live_stock=true`) of a row that has none. Since 2026-09-26 `priority` and
    `priority_order` are the snapshot's, not the row's — there are no such keys here.

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
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "created_by_id": row.created_by_id,
        "updated_by_id": row.updated_by_id,
        "snapshot": (
            serialize_stock_report_item_snapshot(snapshot, row=row)
            if snapshot is not None
            else None
        ),
    }


def serialize_stock_report_item_snapshot(snapshot, *, row) -> dict:
    """One row's frozen demand inside one version.

    `quantity_requested` is the snapshot's own (frozen). The three counters are the
    **row's live values while the snapshot is active** and the snapshot's frozen
    copies once it is closed — the owner's "derive while active, freeze on close"
    ruling (2026-09-26), which is why no assignment move ever writes this table.

    `quantity_awaiting` is the exception on the wire: it is that live/frozen awaiting
    **plus `quantity_resolved`**, the units Scanner processed while the snapshot was
    active. Completion never goes down because Scanner processed a shelf (owner
    ruling 2026-09-26, addendum); it does go down when an assignment leaves awaiting
    for anything else, exactly like MC-5's goal credit.
    """
    active = snapshot.closed_at is None
    return {
        "client_id": snapshot.client_id,
        "version_id": snapshot.version_id,
        "stock_report_item_id": snapshot.stock_report_item_id,
        "quantity_requested": snapshot.quantity_requested,
        "quantity_in_queue": (
            row.quantity_in_queue if active else snapshot.quantity_in_queue
        ),
        "quantity_in_progress": (
            row.quantity_in_progress if active else snapshot.quantity_in_progress
        ),
        "quantity_awaiting": (
            (row.quantity_awaiting if active else snapshot.quantity_awaiting)
            + snapshot.quantity_resolved
        ),
        "quantity_missing": snapshot.quantity_missing,
        "quantity_resolved": snapshot.quantity_resolved,
        "priority": snapshot.priority.value if snapshot.priority is not None else None,
        "priority_order": snapshot.priority_order,
        "active_at": snapshot.active_at.isoformat() if snapshot.active_at else None,
        "closed_at": snapshot.closed_at.isoformat() if snapshot.closed_at else None,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
        "updated_by_id": snapshot.updated_by_id,
    }


def serialize_stock_report_snapshot_version(version) -> dict:
    return {
        "client_id": version.client_id,
        "active_at": version.active_at.isoformat() if version.active_at else None,
        "closed_at": version.closed_at.isoformat() if version.closed_at else None,
        "snapshot_count": version.snapshot_count,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "created_by_id": version.created_by_id,
        "closed_by_id": version.closed_by_id,
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
