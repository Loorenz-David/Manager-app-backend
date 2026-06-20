from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection


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
    }
