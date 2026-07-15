from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.services.commands.tasks._task_state_transitions import (
    maybe_reopen_task_to_working,
)


@pytest.mark.unit
def test_maybe_reopen_task_to_working_moves_ready_task_to_working() -> None:
    task = SimpleNamespace(state=TaskStateEnum.READY, updated_at=None, updated_by_id=None)
    now = datetime.now(timezone.utc)

    changed = maybe_reopen_task_to_working(task, now=now, updated_by_id="usr_actor")

    assert changed is True
    assert task.state == TaskStateEnum.WORKING
    assert task.updated_at == now
    assert task.updated_by_id == "usr_actor"


@pytest.mark.unit
def test_maybe_reopen_task_to_working_does_not_change_non_ready_task() -> None:
    task = SimpleNamespace(state=TaskStateEnum.ASSIGNED, updated_at=None, updated_by_id=None)
    now = datetime.now(timezone.utc)

    changed = maybe_reopen_task_to_working(task, now=now, updated_by_id="usr_actor")

    assert changed is False
    assert task.state == TaskStateEnum.ASSIGNED
    assert task.updated_at is None
    assert task.updated_by_id is None
