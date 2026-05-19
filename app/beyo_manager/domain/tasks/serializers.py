"""Serialization helpers for task domain objects."""

from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.models.tables.tasks.task_step import TaskStep


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