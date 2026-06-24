import pytest

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.task_steps.requests import (
    parse_batch_transition_step_state_request,
)


def _item(step_id: str, task_id: str = "tsk_1") -> dict:
    return {"task_id": task_id, "step_id": step_id}


@pytest.mark.unit
def test_parse_valid_batch_request():
    request = parse_batch_transition_step_state_request(
        {
            "items": [_item("tsp_1"), _item("tsp_2")],
            "new_state": TaskStepStateEnum.WORKING.value,
        }
    )
    assert request.new_state == TaskStepStateEnum.WORKING
    assert [i.step_id for i in request.items] == ["tsp_1", "tsp_2"]


@pytest.mark.unit
def test_parse_rejects_empty_items():
    with pytest.raises(ValidationError):
        parse_batch_transition_step_state_request(
            {"items": [], "new_state": TaskStepStateEnum.WORKING.value}
        )


@pytest.mark.unit
def test_parse_rejects_duplicate_step_ids():
    with pytest.raises(ValidationError):
        parse_batch_transition_step_state_request(
            {
                "items": [_item("tsp_1"), _item("tsp_1")],
                "new_state": TaskStepStateEnum.WORKING.value,
            }
        )


@pytest.mark.unit
def test_parse_rejects_over_cap():
    items = [_item(f"tsp_{i}") for i in range(101)]
    with pytest.raises(ValidationError):
        parse_batch_transition_step_state_request(
            {"items": items, "new_state": TaskStepStateEnum.WORKING.value}
        )
