"""Serialization for upholstery inventory domain objects."""

from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


def serialize_upholstery_inventory(
    inv: UpholsteryInventory,
    image_url: str | None = None,
    upholstery_name: str | None = None,
    upholstery_code: str | None = None,
    page_link: str | None = None,
    supplier_name: str | None = None,
    favorite: bool | None = None,
) -> dict:
    """Serialize an UpholsteryInventory model to JSON-compatible dict."""
    return {
        "client_id": inv.client_id,
        "workspace_id": inv.workspace_id,
        "upholstery_id": inv.upholstery_id,
        "upholstery_name": upholstery_name,
        "upholstery_code": upholstery_code,
        "image_url": image_url,
        "page_link": page_link,
        "supplier_name": supplier_name,
        "favorite": favorite,
        "inventory_condition": inv.inventory_condition.value,
        "current_stored_amount_meters": (
            str(inv.current_stored_amount_meters)
            if inv.current_stored_amount_meters is not None
            else None
        ),
        "current_amount_in_use_meters": (
            str(inv.current_amount_in_use_meters)
            if inv.current_amount_in_use_meters is not None
            else None
        ),
        "current_amount_in_need_meters": (
            str(inv.current_amount_in_need_meters)
            if inv.current_amount_in_need_meters is not None
            else None
        ),
        "current_amount_ordered_meters": (
            str(inv.current_amount_ordered_meters)
            if inv.current_amount_ordered_meters is not None
            else None
        ),
        "total_upholstery_used_meters": (
            str(inv.total_upholstery_used_meters)
            if inv.total_upholstery_used_meters is not None
            else None
        ),
        "total_upholstery_used_inventory_meters": (
            str(inv.total_upholstery_used_inventory_meters)
            if inv.total_upholstery_used_inventory_meters is not None
            else None
        ),
        "total_upholstery_used_surplus_meters": (
            str(inv.total_upholstery_used_surplus_meters)
            if inv.total_upholstery_used_surplus_meters is not None
            else None
        ),
        "total_upholstery_surplus_meters": (
            str(inv.total_upholstery_surplus_meters)
            if inv.total_upholstery_surplus_meters is not None
            else None
        ),
        "low_stock_threshold_meters": (
            str(inv.low_stock_threshold_meters)
            if inv.low_stock_threshold_meters is not None
            else None
        ),
        "minimum_to_have": inv.minimum_to_have,
        "maximum_to_have": inv.maximum_to_have,
        "projected_inventory_value_minor": inv.projected_inventory_value_minor,
        "currency": inv.currency.value if inv.currency else None,
        "planning_position": inv.planning_position,
        "latest_projection_history_id": inv.latest_projection_history_id,
        "created_at": inv.created_at.isoformat(),
        "created_by_id": inv.created_by_id,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        "updated_by_id": inv.updated_by_id,
        "is_deleted": inv.is_deleted,
    }


def serialize_upholstery_inventory_partial(
    inv: UpholsteryInventory,
    image_url: str | None = None,
    upholstery_name: str | None = None,
    upholstery_code: str | None = None,
    page_link: str | None = None,
    supplier_name: str | None = None,
    favorite: bool | None = None,
) -> dict:
    """Serialize a subset of UpholsteryInventory fields for list views."""
    return {
        "client_id": inv.client_id,
        "workspace_id": inv.workspace_id,
        "upholstery_id": inv.upholstery_id,
        "upholstery_name": upholstery_name,
        "upholstery_code": upholstery_code,
        "image_url": image_url,
        "page_link": page_link,
        "supplier_name": supplier_name,
        "favorite": favorite,
        "inventory_condition": inv.inventory_condition.value,
        "current_stored_amount_meters": (
            str(inv.current_stored_amount_meters)
            if inv.current_stored_amount_meters is not None
            else None
        ),
        "current_amount_in_need_meters": (
            str(inv.current_amount_in_need_meters)
            if inv.current_amount_in_need_meters is not None
            else None
        ),
        "current_amount_ordered_meters": (
            str(inv.current_amount_ordered_meters)
            if inv.current_amount_ordered_meters is not None
            else None
        ),
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def serialize_upholstery(
    row: Upholstery,
    inventory: UpholsteryInventory | None = None,
    category: UpholsteryCategory | None = None,
    supplier_name: str | None = None,
) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "code": row.code,
        "image_url": row.image_url,
        "page_link": getattr(row, "page_link", None),
        "favorite": row.favorite,
        "list_order": row.list_order,
        "inventory_id": getattr(inventory, "client_id", None) if inventory is not None else None,
        "current_stored_amount_meters": (
            str(inventory.current_stored_amount_meters)
            if inventory is not None and inventory.current_stored_amount_meters is not None
            else None
        ),
        "current_amount_in_use_meters": (
            str(inventory.current_amount_in_use_meters)
            if inventory is not None and inventory.current_amount_in_use_meters is not None
            else None
        ),
        "current_amount_in_need_meters": (
            str(inventory.current_amount_in_need_meters)
            if inventory is not None and inventory.current_amount_in_need_meters is not None
            else None
        ),
        "current_amount_ordered_meters": (
            str(inventory.current_amount_ordered_meters)
            if inventory is not None and inventory.current_amount_ordered_meters is not None
            else None
        ),
        "inventory_condition": inventory.inventory_condition.value if inventory is not None else None,
        "supplier_name": supplier_name,
        "upholstery_category": {
            "id": category.client_id,
            "name": category.name,
            "image_url": category.image_url,
        } if category is not None else None,
        "origin": "database",
    }


def serialize_upholstery_category(
    cat: UpholsteryCategory,
    upholstery_count: int | None = None,
) -> dict:
    result = {
        "client_id": cat.client_id,
        "workspace_id": cat.workspace_id,
        "name": cat.name,
        "image_url": cat.image_url,
        "favorite": cat.favorite,
        "created_at": cat.created_at.isoformat(),
        "created_by_id": cat.created_by_id,
        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
        "updated_by_id": cat.updated_by_id,
        "is_deleted": cat.is_deleted,
    }
    if upholstery_count is not None:
        result["upholstery_count"] = upholstery_count
    return result


# ---------------------------------------------------------------------------
# Inventory history (ledger) timeline
# ---------------------------------------------------------------------------


def _history_snapshot(rec, phase: str) -> dict | None:
    from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import INVENTORY_BUCKETS

    values = {bucket: getattr(rec, f"{phase}_{bucket}_meters") for bucket in INVENTORY_BUCKETS}
    if all(v is None for v in values.values()):
        return None
    return values


def _str_or_none(value) -> str | None:
    return None if value is None else str(value)


def serialize_inventory_buckets(values: dict | None) -> dict | None:
    if values is None:
        return None
    return {bucket: _str_or_none(value) for bucket, value in values.items()}


def inventory_history_delta(before: dict | None, after: dict | None) -> dict | None:
    """Per-bucket after − before; None unless both snapshots exist."""
    if before is None or after is None:
        return None
    from decimal import Decimal

    return {
        bucket: (after[bucket] or Decimal("0")) - (before[bucket] or Decimal("0"))
        for bucket in after
    }


def serialize_inventory_history_record(
    rec,
    *,
    users: dict,
    tasks: dict,
    items: dict,
    orders: dict,
    task_id: str | None,
    task_resolution: str | None,
    chain_break: bool = False,
    children: list[dict] | None = None,
) -> dict:
    """One ledger row for the inventory timeline.

    ``task_id`` / ``task_resolution`` come from the query: "recorded" when the row stored the
    task at write time, "inferred" when the query resolved it from the item afterwards.
    """
    from beyo_manager.domain.history.serializers import serialize_record_actor

    before = _history_snapshot(rec, "before")
    after = _history_snapshot(rec, "after")
    task = tasks.get(task_id) if task_id else None
    item = items.get(rec.item_id) if rec.item_id else None
    order = orders.get(rec.upholstery_order_id) if rec.upholstery_order_id else None

    out = {
        "client_id": rec.client_id,
        "movement_type": rec.movement_type.value,
        "trigger": rec.trigger,
        "created_at": rec.created_at.isoformat(),
        "is_reconstructed": rec.is_reconstructed,
        "created_by": serialize_record_actor(
            users.get(rec.created_by_id) if rec.created_by_id else None,
            rec.created_by_id,
            rec.username_snapshot,
        ),
        "quantity_meters": _str_or_none(rec.quantity_meters),
        "before": serialize_inventory_buckets(before),
        "after": serialize_inventory_buckets(after),
        "delta": serialize_inventory_buckets(inventory_history_delta(before, after)),
        "requirement": (
            {
                "client_id": rec.requirement_id,
                "from_state": rec.requirement_from_state.value if rec.requirement_from_state else None,
                "to_state": rec.requirement_to_state.value if rec.requirement_to_state else None,
            }
            if rec.requirement_id or rec.requirement_from_state or rec.requirement_to_state
            else None
        ),
        "task": (
            {
                "client_id": task.client_id,
                "task_scalar_id": task.task_scalar_id,
                "title": task.title,
                "state": task.state.value,
                "is_deleted": task.is_deleted,
            }
            if task is not None
            else None
        ),
        "task_resolution": task_resolution if task is not None else None,
        "item": (
            {
                "client_id": item.client_id,
                "article_number": item.article_number,
                "sku": item.sku,
                "item_category_snapshot": item.item_category_snapshot,
            }
            if item is not None
            else None
        ),
        "upholstery_order": (
            {
                "client_id": order.client_id,
                "state": order.state.value,
                "order_amount_meters": _str_or_none(order.order_amount_meters),
                "received_amount_meters": _str_or_none(order.received_amount_meters),
            }
            if order is not None
            else None
        ),
        "anomaly": rec.anomaly,
        "note": rec.note,
        "details": rec.details,
        "chain_break": chain_break,
    }
    if children is not None:
        out["children"] = children
    return out
