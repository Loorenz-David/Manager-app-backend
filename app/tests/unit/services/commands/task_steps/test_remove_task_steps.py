from types import SimpleNamespace

import pytest

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum
from beyo_manager.services.commands.task_steps.remove_task_step import (
    _apply_removed_dependency_counts,
    _count_removed_prerequisite_edges,
)


def _edge(dependent_step_id: str, prerequisite_step_id: str):
    return SimpleNamespace(
        dependent_step_id=dependent_step_id,
        prerequisite_step_id=prerequisite_step_id,
    )


def _step(
    *,
    total_dependencies: int,
    completed_dependencies: int,
    readiness_status: TaskStepReadinessStatusEnum,
):
    return SimpleNamespace(
        total_dependencies=total_dependencies,
        completed_dependencies=completed_dependencies,
        readiness_status=readiness_status,
    )


@pytest.mark.unit
def test_count_removed_prerequisite_edges_skips_deleted_dependents_and_counts_completed():
    edges = [
        _edge("tsp_dep_a", "tsp_prereq_done"),
        _edge("tsp_dep_a", "tsp_prereq_pending"),
        _edge("tsp_dep_b", "tsp_prereq_pending"),
        _edge("tsp_removed_too", "tsp_prereq_done"),
    ]

    counts = _count_removed_prerequisite_edges(
        edges=edges,
        removed_step_ids={"tsp_prereq_done", "tsp_prereq_pending", "tsp_removed_too"},
        completed_removed_step_ids={"tsp_prereq_done"},
    )

    assert counts == {
        "tsp_dep_a": (2, 1),
        "tsp_dep_b": (1, 0),
    }


@pytest.mark.unit
def test_apply_removed_dependency_counts_decrements_completed_dependencies_correctly():
    step = _step(
        total_dependencies=3,
        completed_dependencies=1,
        readiness_status=TaskStepReadinessStatusEnum.PARTIAL,
    )

    _apply_removed_dependency_counts(
        step,
        removed_total=1,
        removed_completed=1,
    )

    assert step.total_dependencies == 2
    assert step.completed_dependencies == 0
    assert step.readiness_status == TaskStepReadinessStatusEnum.BLOCKED
