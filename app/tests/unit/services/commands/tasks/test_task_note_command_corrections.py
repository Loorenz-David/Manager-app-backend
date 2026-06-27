import pytest

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.tasks.append_note_read_by import append_note_read_by
from beyo_manager.services.commands.tasks.create_task_note import create_task_note
from beyo_manager.services.context import ServiceContext


class _FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeScalarOneOrNoneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSessionForReadBy:
    def __init__(self, note):
        self.note = note

    def in_transaction(self):
        return False

    def begin(self):
        return _FakeBegin()

    async def execute(self, _statement):
        return _FakeScalarOneOrNoneResult(self.note)


@pytest.mark.unit
async def test_create_task_note_rejects_empty_notes_list():
    ctx = ServiceContext(
        identity={"user_id": "usr_1", "workspace_id": "wrk_1"},
        incoming_data={"task_id": "tsk_1", "notes": []},
        session=object(),
    )

    with pytest.raises(ValidationError, match="notes list must not be empty."):
        await create_task_note(ctx)


@pytest.mark.unit
async def test_append_note_read_by_rejects_note_from_different_task():
    note = type("Note", (), {"task_id": "tsk_other", "users_read_list": [], "client_id": "tno_1"})()
    ctx = ServiceContext(
        identity={"user_id": "usr_1", "workspace_id": "wrk_1"},
        incoming_data={"client_id": "tno_1", "task_id": "tsk_1", "user_ids": ["usr_1"]},
        session=_FakeSessionForReadBy(note),
    )

    with pytest.raises(NotFound, match="Task note not found."):
        await append_note_read_by(ctx)
