from types import SimpleNamespace

import pytest

from beyo_manager.domain.task_steps.enums import (
    TaskStepReadinessStatusEnum,
    TaskStepStateEnum,
)
from beyo_manager.services.commands.task_steps._wire_new_step_dependencies import (
    _compute_dependency_edges,
)


def _step(
    client_id: str,
    section_id: str,
    *,
    state: TaskStepStateEnum = TaskStepStateEnum.PENDING,
    readiness: TaskStepReadinessStatusEnum = TaskStepReadinessStatusEnum.READY,
    total_dependencies: int = 0,
    completed_dependencies: int = 0,
):
    return SimpleNamespace(
        client_id=client_id,
        working_section_id=section_id,
        state=state,
        readiness_status=readiness,
        total_dependencies=total_dependencies,
        completed_dependencies=completed_dependencies,
    )


@pytest.mark.unit
def test_compute_dependency_edges_wires_new_step_to_existing_and_new_prereqs():
    existing_prereq = _step(
        "tsp_existing_prereq",
        "sec_a",
        state=TaskStepStateEnum.COMPLETED,
    )
    new_prereq = _step("tsp_new_prereq", "sec_a")
    new_dependent = _step("tsp_new_dependent", "sec_b")

    edges, readiness_changed = _compute_dependency_edges(
        new_steps=[new_prereq, new_dependent],
        existing_steps=[existing_prereq],
        section_prereqs={"sec_b": {"sec_a"}},
    )

    assert [(dep.client_id, prereq.client_id) for dep, prereq in edges] == [
        ("tsp_new_dependent", "tsp_existing_prereq"),
        ("tsp_new_dependent", "tsp_new_prereq"),
    ]
    assert new_dependent.total_dependencies == 2
    assert new_dependent.completed_dependencies == 1
    assert new_dependent.readiness_status == TaskStepReadinessStatusEnum.PARTIAL
    assert readiness_changed == []


@pytest.mark.unit
def test_compute_dependency_edges_recalculates_existing_dependents_for_new_prereqs():
    new_prereq = _step("tsp_new_prereq", "sec_a")
    existing_dependent = _step("tsp_existing_dependent", "sec_b")
    terminal_dependent = _step(
        "tsp_terminal",
        "sec_b",
        state=TaskStepStateEnum.COMPLETED,
    )

    edges, readiness_changed = _compute_dependency_edges(
        new_steps=[new_prereq],
        existing_steps=[existing_dependent, terminal_dependent],
        section_prereqs={"sec_b": {"sec_a"}},
    )

    assert [(dep.client_id, prereq.client_id) for dep, prereq in edges] == [
        ("tsp_existing_dependent", "tsp_new_prereq"),
    ]
    assert existing_dependent.total_dependencies == 1
    assert existing_dependent.completed_dependencies == 0
    assert existing_dependent.readiness_status == TaskStepReadinessStatusEnum.BLOCKED
    assert readiness_changed == [existing_dependent]
    assert terminal_dependent.total_dependencies == 0
