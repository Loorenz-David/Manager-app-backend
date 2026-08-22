from beyo_manager.domain.item_economics.budget_division import participating_sections
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep


def task_step(client_id, section, state, is_deleted=False):
    return TaskStep(
        client_id=client_id,
        workspace_id="ws_test",
        task_id="task_test",
        working_section_id=section,
        state=state,
        is_deleted=is_deleted,
    )


def test_participating_sections_uses_real_task_steps_and_excludes_deleted_or_terminal_states():
    steps = [
        task_step("a", "A", TaskStepStateEnum.COMPLETED),
        task_step("b", "B", TaskStepStateEnum.WORKING),
        task_step("c", "C", TaskStepStateEnum.FAILED),
        task_step("d", "D", TaskStepStateEnum.COMPLETED, is_deleted=True),
        task_step("e1", "E", TaskStepStateEnum.SKIPPED),
        task_step("e2", "E", TaskStepStateEnum.CANCELLED),
    ]
    assert participating_sections(steps) == frozenset({"A", "B"})
