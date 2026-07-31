from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.domain.users.serializers import serialize_user_working_section_member


def serialize_task_step_compact(step: TaskStep, working_section: WorkingSection | None) -> dict:
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
        "working_section_name": working_section.name if working_section else None,
        "working_section_image": working_section.image if working_section else None,
        "created_at": step.created_at.isoformat() if step.created_at else None,
        "closed_at": step.closed_at.isoformat() if step.closed_at else None,
        "ready_by_at": step.ready_by_at.isoformat() if step.ready_by_at else None,
    }


def serialize_task_step_acknowledgment(
    ack: TaskStepAcknowledgment,
    *,
    worker: User | None = None,
    created_by: User | None = None,
) -> dict:
    return {
        "client_id": ack.client_id,
        "step_id": ack.step_id,
        "task_id": ack.task_id,
        "reason": ack.reason,
        "worker": serialize_user_working_section_member(worker) if worker else None,
        "created_by": serialize_user_working_section_member(created_by) if created_by else None,
        "first_seen_at": ack.first_seen_at.isoformat() if ack.first_seen_at else None,
        "acknowledged_at": ack.acknowledged_at.isoformat() if ack.acknowledged_at else None,
        "created_at": ack.created_at.isoformat(),
    }
