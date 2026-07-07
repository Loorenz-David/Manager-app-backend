"""Serialization for item upholstery domain objects."""

from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement


def serialize_item_upholstery(
    iup: ItemUpholstery,
    requirements: list[ItemUpholsteryRequirement],
) -> dict:
    """Serialize an ItemUpholstery model to JSON-compatible dict."""
    return {
        "client_id": iup.client_id,
        "workspace_id": iup.workspace_id,
        "item_id": iup.item_id,
        "upholstery_id": iup.upholstery_id,
        "name": iup.name,
        "code": iup.code,
        "amount_meters": str(iup.amount_meters) if iup.amount_meters is not None else None,
        "source": iup.source.value,
        "time_to_fix_in_seconds": iup.time_to_fix_in_seconds,
        "active_requirement_id": iup.active_requirement_id,
        "created_at": iup.created_at.isoformat(),
        "created_by_id": iup.created_by_id,
        "updated_at": iup.updated_at.isoformat() if iup.updated_at else None,
        "updated_by_id": iup.updated_by_id,
        "is_deleted": iup.is_deleted,
        "item_upholstery_requirements": [
            serialize_upholstery_requirement(r) for r in requirements
        ],
    }


def serialize_upholstery_requirement(req: ItemUpholsteryRequirement) -> dict:
    """Serialize an ItemUpholsteryRequirement model to JSON-compatible dict."""
    return {
        "client_id": req.client_id,
        "workspace_id": req.workspace_id,
        "item_upholstery_id": req.item_upholstery_id,
        "upholstery_inventory_id": req.upholstery_inventory_id,
        "amount_meters": str(req.amount_meters) if req.amount_meters is not None else None,
        "source": req.source.value,
        "state": req.state.value,
        "value_minor": req.value_minor,
        "currency": req.currency.value if req.currency else None,
        "created_at": req.created_at.isoformat(),
        "created_by_id": req.created_by_id,
        "ordered_at": req.ordered_at.isoformat() if req.ordered_at else None,
        "in_use_at": req.in_use_at.isoformat() if req.in_use_at else None,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "failed_at": req.failed_at.isoformat() if req.failed_at else None,
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        "updated_by_id": req.updated_by_id,
        "is_deleted": req.is_deleted,
    }


def serialize_item_issue(issue: ItemIssue) -> dict:
    return {
        "client_id": issue.client_id,
        "workspace_id": issue.workspace_id,
        "item_id": issue.item_id,
        "step_id": issue.step_id,
        "worker_id": issue.worker_id,
        "working_section_id": issue.working_section_id,
        "item_category_id": issue.item_category_id,
        "issue_type_id": issue.issue_type_id,
        "issue_type_snapshot": issue.issue_type_snapshot,
        "issue_mode_snapshot": issue.issue_mode_snapshot,
        "placement_of_issue_snapshot": issue.placement_of_issue_snapshot,
        "intensity": issue.intensity,
        "created_at": issue.created_at.isoformat(),
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }


def _build_item_category_object(item: Item) -> dict | None:
    if item.item_category_id is None:
        return None
    return {
        "client_id": item.item_category_id,
        "name": item.item_category_snapshot,
        "major_category": item.item_major_category_snapshot,
    }


def _serialize_item_base(item: Item) -> dict:
    return {
        "client_id": item.client_id,
        "workspace_id": item.workspace_id,
        "article_number": item.article_number,
        "sku": item.sku,
        "state": item.state.value,
        "item_category": _build_item_category_object(item),
        "quantity": item.quantity,
        "designer": item.designer,
        "height_in_cm": item.height_in_cm,
        "width_in_cm": item.width_in_cm,
        "depth_in_cm": item.depth_in_cm,
        "item_value_minor": item.item_value_minor,
        "item_cost_minor": item.item_cost_minor,
        "item_currency": item.item_currency.value if item.item_currency else None,
        "item_position": item.item_position,
        "item_zone": item.item_zone,
        "external_id": item.external_id,
        "external_url": item.external_url,
        "external_source": item.external_source,
        "external_order_id": item.external_order_id,
        "created_at": item.created_at.isoformat(),
        "created_by_id": item.created_by_id,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "updated_by_id": item.updated_by_id,
    }


def serialize_item_list(item: Item, issue_count: int) -> dict:
    return {**_serialize_item_base(item), "issue_count": issue_count}


def serialize_item_detail(
    item: Item,
    issues: list[ItemIssue],
    upholstery: ItemUpholstery | None,
    requirements: list[ItemUpholsteryRequirement],
) -> dict:
    return {
        **_serialize_item_base(item),
        "item_issues": [serialize_item_issue(issue) for issue in issues],
        "item_upholstery": serialize_item_upholstery(upholstery, requirements) if upholstery is not None else None,
    }


def serialize_item_category(category: ItemCategory) -> dict:
    return {
        "client_id": category.client_id,
        "name": category.name,
        "major_category": category.major_category.value,
        "created_at": category.created_at.isoformat(),
        "created_by_id": category.created_by_id,
        "image_url": category.image_url,
    }
