import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.tasks.requests import (
    parse_create_batch_task_notes_request,
    parse_create_task_note_request,
    parse_mark_note_read_by_request,
    parse_update_task_note_request,
)


@pytest.mark.unit
def test_parse_create_task_note_request_accepts_block_list_plain_text_and_users_read_list():
    request = parse_create_task_note_request(
        {
            "task_id": "tsk_1",
            "note_type": "user_note",
            "content": [{"type": "text", "text": "hello"}],
            "plain_text": "hello",
            "users_read_list": ["usr_1", "usr_2"],
        }
    )

    assert request.task_id == "tsk_1"
    assert request.content == [{"type": "text", "text": "hello"}]
    assert request.plain_text == "hello"
    assert request.users_read_list == ["usr_1", "usr_2"]


@pytest.mark.unit
def test_parse_update_task_note_request_accepts_plain_text_and_optional_content():
    request = parse_update_task_note_request(
        {
            "client_id": "tno_1",
            "plain_text": "updated",
            "content": [{"type": "text", "text": "updated"}],
        }
    )

    assert request.client_id == "tno_1"
    assert request.plain_text == "updated"
    assert request.content == [{"type": "text", "text": "updated"}]


@pytest.mark.unit
def test_parse_create_task_note_request_rejects_dict_content():
    with pytest.raises(ValidationError, match="content: Input should be a valid list"):
        parse_create_task_note_request(
            {
                "task_id": "tsk_1",
                "note_type": "user_note",
                "content": {"type": "text", "text": "hello"},
            }
        )


@pytest.mark.unit
def test_parse_mark_note_read_by_request_accepts_string_list():
    request = parse_mark_note_read_by_request(
        {
            "client_id": "tno_1",
            "task_id": "tsk_1",
            "user_ids": ["usr_1", "usr_2"],
        }
    )

    assert request.client_id == "tno_1"
    assert request.task_id == "tsk_1"
    assert request.user_ids == ["usr_1", "usr_2"]


@pytest.mark.unit
def test_parse_create_batch_task_notes_request_accepts_notes_array():
    request = parse_create_batch_task_notes_request(
        {
            "task_id": "tsk_1",
            "notes": [
                {
                    "client_id": "tno_1",
                    "note_type": "user_note",
                    "content": [{"type": "text", "text": "first"}],
                    "plain_text": "first",
                },
                {
                    "note_type": "system_note",
                    "content": [{"type": "text", "text": "second"}],
                    "plain_text": "second",
                    "users_read_list": ["usr_1"],
                },
            ],
        }
    )

    assert request.task_id == "tsk_1"
    assert len(request.notes) == 2
    assert request.notes[0].client_id == "tno_1"
    assert request.notes[1].users_read_list == ["usr_1"]
