"""Serialization helpers for task domain objects."""

from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User


def serialize_task(task: Task) -> dict:
    return {
        "client_id": task.client_id,
        "task_scalar_id": task.task_scalar_id,
        "task_type": task.task_type.value,
        "priority": task.priority.value,
        "state": task.state.value,
        "title": task.title,
        "summary": task.summary,
        "return_source": task.return_source.value if task.return_source else None,
        "item_location": task.item_location.value if task.item_location else None,
        "return_method": task.return_method.value if task.return_method else None,
        "fulfillment_method": task.fulfillment_method.value if task.fulfillment_method else None,
        "additional_details": task.additional_details,
        "ready_by_at": task.ready_by_at.isoformat() if task.ready_by_at else None,
        "scheduled_start_at": task.scheduled_start_at.isoformat() if task.scheduled_start_at else None,
        "scheduled_end_at": task.scheduled_end_at.isoformat() if task.scheduled_end_at else None,
        "customer_id": task.customer_id,
        "primary_phone_number": task.primary_phone_number,
        "secondary_phone_number": task.secondary_phone_number,
        "primary_email": task.primary_email,
        "secondary_email": task.secondary_email,
        "address": task.address,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "closed_at": task.closed_at.isoformat() if task.closed_at else None,
        "is_deleted": task.is_deleted,
        "deleted_at": task.deleted_at.isoformat() if task.deleted_at else None,
    }


def serialize_item(item: Item | None) -> dict | None:
    if item is None:
        return None
    return {
        "client_id": item.client_id,
        "article_number": item.article_number,
        "sku": item.sku,
        "state": item.state.value,
        "item_category_id": item.item_category_id,
        "quantity": item.quantity,
        "designer": item.designer,
        "height_in_cm": item.height_in_cm,
        "width_in_cm": item.width_in_cm,
        "depth_in_cm": item.depth_in_cm,
        "item_value_minor": item.item_value_minor,
        "item_cost_minor": item.item_cost_minor,
        "item_currency": item.item_currency.value if item.item_currency else None,
        "item_position": item.item_position,
        "external_id": item.external_id,
        "external_url": item.external_url,
        "external_source": item.external_source,
        "external_order_id": item.external_order_id,
        "item_category_snapshot": item.item_category_snapshot,
        "item_major_category_snapshot": item.item_major_category_snapshot,
    }


def serialize_item_issue(row: ItemIssue) -> dict:
    return {
        "client_id": row.client_id,
        "item_id": row.item_id,
        "issue_type_id": row.issue_type_id,
        "issue_severity_id": row.issue_severity_id,
        "state": row.state.value,
        "base_time_seconds": row.base_time_seconds,
        "time_multiplier": float(row.time_multiplier) if row.time_multiplier is not None else None,
        "issue_name_snapshot": row.issue_name_snapshot,
        "severity_name_snapshot": row.severity_name_snapshot,
        "created_by_id": row.created_by_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_upholstery(row: ItemUpholstery) -> dict:
    return {
        "client_id": row.client_id,
        "item_id": row.item_id,
        "upholstery_id": row.upholstery_id,
        "name": row.name,
        "code": row.code,
        "amount_meters": float(row.amount_meters) if row.amount_meters is not None else None,
        "source": row.source.value,
        "time_to_fix_in_seconds": row.time_to_fix_in_seconds,
        "active_requirement_id": row.active_requirement_id,
    }


def serialize_requirement(row: ItemUpholsteryRequirement) -> dict:
    return {
        "client_id": row.client_id,
        "item_upholstery_id": row.item_upholstery_id,
        "upholstery_inventory_id": row.upholstery_inventory_id,
        "amount_meters": float(row.amount_meters) if row.amount_meters is not None else None,
        "value_minor": row.value_minor,
        "currency": row.currency.value if row.currency else None,
        "source": row.source.value,
        "state": row.state.value,
    }


def serialize_step(step: TaskStep) -> dict:
    return {
        "client_id": step.client_id,
        "task_id": step.task_id,
        "state": step.state.value,
        "readiness_status": step.readiness_status.value,
        "sequence_order": step.sequence_order,
        "working_section_id": step.working_section_id,
        "assigned_worker_id": step.assigned_worker_id,
        "total_dependencies": step.total_dependencies,
        "completed_dependencies": step.completed_dependencies,
        "working_section_name_snapshot": step.working_section_name_snapshot,
        "assigned_worker_display_name_snapshot": step.assigned_worker_display_name_snapshot,
        "created_at": step.created_at.isoformat() if step.created_at else None,
        "closed_at": step.closed_at.isoformat() if step.closed_at else None,
    }


def serialize_step_latest_state_record(record: StepStateRecord | None) -> dict | None:
    if record is None:
        return None
    return {
        "id": record.client_id,
        "step_id": record.step_id,
        "state": record.state.value,
        "reason": record.reason.value if record.reason else None,
        "entered_at": record.entered_at.isoformat() if record.entered_at else None,
        "exited_at": record.exited_at.isoformat() if record.exited_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "created_by_id": record.created_by_id,
        "description": record.description,
        "accuracy": record.accuracy,
        "accuracy_measured_by": record.accuracy_measured_by.value if record.accuracy_measured_by else None,
        "taken_from_average": record.taken_from_average,
    }


def serialize_note(note: TaskNote) -> dict:
    return {
        "client_id": note.client_id,
        "task_id": note.task_id,
        "note_type": note.note_type.value,
        "content": note.content,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        "is_deleted": note.is_deleted,
        "deleted_at": note.deleted_at.isoformat() if note.deleted_at else None,
    }


def _serialize_flow_record_user(user: User | None, created_by_id: str | None, username_snapshot: str | None = None) -> dict | None:
    if created_by_id is None:
        return None
    if user is not None:
        return {
            "client_id": user.client_id,
            "username": user.username,
            "profile_picture": user.profile_picture,
        }
    return {
        "client_id": created_by_id,
        "username": username_snapshot,
        "profile_picture": None,
    }


def serialize_history_flow_record(record: HistoryRecord, link: HistoryRecordLink, users_map: dict) -> dict:
    user = users_map.get(record.created_by_id) if record.created_by_id else None
    return {
        "type": "history_record",
        "entity_type": link.entity_type.value,
        "entity_client_id": link.entity_client_id,
        "description": record.description,
        "created_at": record.created_at.isoformat(),
        "created_by": _serialize_flow_record_user(user, record.created_by_id, record.username_snapshot),
    }


def serialize_step_flow_record(ssr: StepStateRecord, step: TaskStep, users_map: dict) -> dict:
    user = users_map.get(ssr.created_by_id) if ssr.created_by_id else None
    username = user.username if user else (ssr.created_by_id or "Unknown")
    working_section_name = step.working_section_name_snapshot or ""
    description = f"{username} marked {ssr.state.value} on working section {working_section_name}".rstrip()
    return {
        "type": "task_step",
        "entity_type": "task_step",
        "entity_client_id": ssr.step_id,
        "description": description,
        "created_at": ssr.created_at.isoformat(),
        "created_by": _serialize_flow_record_user(user, ssr.created_by_id),
    }


def serialize_task_light(task: Task) -> dict:
    return {
        "client_id": task.client_id,
        "task_type": task.task_type.value,
        "priority": task.priority.value,
        "state": task.state.value,
        "return_source": task.return_source.value if task.return_source else None,
        "item_location": task.item_location.value if task.item_location else None,
        "ready_by_at": task.ready_by_at.isoformat() if task.ready_by_at else None,
        "return_method": task.return_method.value if task.return_method else None,
    }


def serialize_step_state_record_light(record: StepStateRecord | None) -> dict | None:
    if record is None:
        return None
    return {
        "state": record.state.value,
        "entered_at": record.entered_at.isoformat() if record.entered_at else None,
        "exited_at": record.exited_at.isoformat() if record.exited_at else None,
    }


def serialize_item_worker_light(
    item: Item | None,
    upholstery_requirements: list[ItemUpholsteryRequirement] | None = None,
    upholsteries_by_id: dict[str, ItemUpholstery] | None = None,
) -> dict | None:
    if item is None:
        return None
    return {
        "client_id": item.client_id,
        "article_number": item.article_number,
        "sku": item.sku,
        "state": item.state.value,
        "item_category_id": item.item_category_id,
        "quantity": item.quantity,
        "item_position": item.item_position,
        "upholstery_requirement": [
            {
                "client_id": req.client_id,
                "item_upholstery_id": req.item_upholstery_id,
                "upholstery_id": (
                    upholsteries_by_id[req.item_upholstery_id].upholstery_id
                    if upholsteries_by_id and req.item_upholstery_id in upholsteries_by_id
                    else None
                ),
                "state": req.state.value,
                "source": req.source.value,
                "amount_meters": float(req.amount_meters) if req.amount_meters is not None else None,
            }
            for req in (upholstery_requirements or [])
        ],
    }