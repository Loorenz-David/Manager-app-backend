"""Serialization for upholstery inventory domain objects."""

from beyo_manager.domain.images.serializers import serialize_image_light
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


def serialize_upholstery_inventory(inv: UpholsteryInventory) -> dict:
    """Serialize an UpholsteryInventory model to JSON-compatible dict."""
    return {
        "client_id": inv.client_id,
        "workspace_id": inv.workspace_id,
        "upholstery_id": inv.upholstery_id,
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


def serialize_upholstery(
    row: Upholstery,
    primary_image: Image | None = None,
    inventory: UpholsteryInventory | None = None,
) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "code": row.code,
        "image_url": serialize_image_light(primary_image)["image_url"] if primary_image else None,
        "current_stored_amount_meters": (
            str(inventory.current_stored_amount_meters)
            if inventory is not None and inventory.current_stored_amount_meters is not None
            else None
        ),
        "inventory_condition": inventory.inventory_condition.value if inventory is not None else None,
    }
