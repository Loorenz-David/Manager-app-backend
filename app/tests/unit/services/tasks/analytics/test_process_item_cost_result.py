from dataclasses import asdict, FrozenInstanceError

import pytest

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.item_cost_result import ItemCostResultPayload
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.services.infra.execution.task_router import QUEUE_MAP
from beyo_manager.services.tasks.analytics.process_item_cost_result import _ADMITTED_STATES
from beyo_manager.workers.analytics_worker import HANDLER_MAP, handle_process_item_cost_result


def test_result_task_payload_is_frozen_and_exactly_scoped() -> None:
    payload = ItemCostResultPayload(workspace_id="ws", task_id="task")

    assert asdict(payload) == {"workspace_id": "ws", "task_id": "task"}
    with pytest.raises(FrozenInstanceError):
        payload.task_id = "other"


def test_result_task_type_and_admitted_states_cover_ready_and_terminal_states() -> None:
    assert TaskType.PROCESS_ITEM_COST_RESULT.value == "process_item_cost_result"
    assert {
        TaskStateEnum.WORKING,
        TaskStateEnum.READY,
        TaskStateEnum.RESOLVED,
        TaskStateEnum.FAILED,
        TaskStateEnum.CANCELLED,
    } == _ADMITTED_STATES
    assert {
        TaskStateEnum.PENDING,
        TaskStateEnum.ASSIGNED,
        TaskStateEnum.STALLED,
    } == set(TaskStateEnum) - _ADMITTED_STATES


def test_c10_result_handler_is_registered_on_the_analytics_route() -> None:
    assert QUEUE_MAP[TaskType.PROCESS_ITEM_COST_RESULT] == "queue:analytics"
    assert HANDLER_MAP[TaskType.PROCESS_ITEM_COST_RESULT] is handle_process_item_cost_result
