from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.services.commands.tasks.requests import parse_create_task_request


def test_parse_create_task_request_keeps_assortment() -> None:
    request = parse_create_task_request(
        {
            "task_type": TaskTypeEnum.RETURN,
            "assortment": "Large sofa set",
        }
    )

    assert request.assortment == "Large sofa set"
