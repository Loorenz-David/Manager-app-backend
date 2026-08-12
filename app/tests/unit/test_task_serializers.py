from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.serializers import (
    include_monetary_step_fields,
    serialize_step,
    serialize_task_light,
)


@pytest.mark.unit
def test_serialize_task_light_includes_task_schedule_fields():
    task = SimpleNamespace(
        client_id="tsk_1",
        task_type=SimpleNamespace(value="repair"),
        priority=SimpleNamespace(value="high"),
        state=SimpleNamespace(value="open"),
        return_source=None,
        item_location=None,
        ready_by_at=datetime(2026, 6, 25, 12, 30, tzinfo=timezone.utc),
        scheduled_start_at=datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc),
        scheduled_end_at=datetime(2026, 6, 26, 11, 0, tzinfo=timezone.utc),
        return_method=None,
        assortment="three_seater",
    )

    result = serialize_task_light(task)

    assert result["ready_by_at"] == "2026-06-25T12:30:00+00:00"
    assert result["scheduled_start_at"] == "2026-06-26T09:00:00+00:00"
    assert result["scheduled_end_at"] == "2026-06-26T11:00:00+00:00"
    assert result["assortment"] == "three_seater"


def _step_stub():
    return SimpleNamespace(
        client_id="tsp_1",
        task_id="tsk_1",
        state=TaskStepStateEnum.PENDING,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        sequence_order=1,
        working_section_id="wsec_1",
        assigned_worker_id=None,
        total_dependencies=0,
        completed_dependencies=0,
        working_section_name_snapshot="Section",
        assigned_worker_display_name_snapshot=None,
        created_at=None,
        closed_at=None,
        ready_by_at=None,
        total_working_seconds=0,
        total_pause_seconds=0,
        total_ended_shift_seconds=0,
        total_working_count=0,
        total_pause_count=0,
        total_ended_shift_count=0,
        total_issues_count=0,
        total_issues_resolved_count=0,
        total_cost_minor=4321,
        recorded_time_marked_wrong=False,
    )


@pytest.mark.unit
def test_serialize_step_requires_declared_money_boundary():
    with pytest.raises(TypeError):
        serialize_step(_step_stub())

    assert "total_cost_minor" not in serialize_step(_step_stub(), include_monetary=False)
    assert serialize_step(_step_stub(), include_monetary=True)["total_cost_minor"] == 4321


@pytest.mark.unit
@pytest.mark.parametrize(
    "role_name, expected",
    [
        (RoleNameEnum.ADMIN.value, True),
        (RoleNameEnum.MANAGER.value, True),
        (RoleNameEnum.WORKER.value, False),
        (RoleNameEnum.SELLER.value, False),
        ("", False),
        ("unknown", False),
    ],
)
def test_money_boundary_role_derivation_is_allow_list(role_name, expected):
    assert include_monetary_step_fields(role_name) is expected
