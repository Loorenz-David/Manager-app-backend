import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import tasks as tasks_router


@pytest.mark.unit
async def test_route_create_note_wraps_batch_notes_under_notes_key(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"client_ids": ["tno_1", "tno_2"]}, error=None)

    monkeypatch.setattr(tasks_router, "run_service", _fake_run_service)

    result = await tasks_router.route_create_note(
        task_id="tsk_1",
        body=[
            tasks_router._TaskNoteInputBody(
                client_id="tno_1",
                note_type="user_note",
                content=[{"type": "text", "text": "First"}],
                plain_text="First",
            ),
            tasks_router._TaskNoteInputBody(
                note_type="system_note",
                content=[{"type": "text", "text": "Second"}],
                plain_text="Second",
                users_read_list=["usr_1"],
            ),
        ],
        claims={"user_id": "usr_1", "role_name": "manager"},
        session=object(),
    )

    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload["ok"] is True
    assert payload["data"]["client_ids"] == ["tno_1", "tno_2"]
    assert captured["command"] is tasks_router.create_task_note
    assert captured["ctx"].incoming_data == {
        "task_id": "tsk_1",
        "notes": [
            {
                "client_id": "tno_1",
                "note_type": tasks_router.TaskNoteTypeEnum.USER_NOTE,
                "content": [{"type": "text", "text": "First"}],
                "plain_text": "First",
                "users_read_list": None,
            },
            {
                "client_id": None,
                "note_type": tasks_router.TaskNoteTypeEnum.SYSTEM_NOTE,
                "content": [{"type": "text", "text": "Second"}],
                "plain_text": "Second",
                "users_read_list": ["usr_1"],
            },
        ],
    }

