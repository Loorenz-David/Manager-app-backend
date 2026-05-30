import pytest

from beyo_manager.services.commands.cases.requests import parse_create_case_request


@pytest.mark.unit
def test_parse_create_case_request_accepts_selected_all_optional():
    request = parse_create_case_request(
        {
            "case_type_id": "cty_1",
            "participants": ["usr_1", "usr_2"],
            "selected_all": True,
            "skip_participants": ["usr_3"],
        }
    )

    assert request.case_type_id == "cty_1"
    assert request.participants == ["usr_1", "usr_2"]
    assert request.selected_all is True
    assert request.skip_participants == ["usr_3"]


@pytest.mark.unit
def test_parse_create_case_request_defaults_selected_all_to_none():
    request = parse_create_case_request({"participants": ["usr_1"]})

    assert request.participants == ["usr_1"]
    assert request.selected_all is None
    assert request.skip_participants is None


@pytest.mark.unit
def test_parse_create_case_request_accepts_initial_message():
    request = parse_create_case_request(
        {
            "initial_message": {
                "client_id": "ccm_1",
                "content": [{"type": "text", "text": "hello"}],
                "plain_text": "hello",
            }
        }
    )

    assert request.initial_message is not None
    assert request.initial_message.client_id == "ccm_1"
    assert request.initial_message.plain_text == "hello"
    assert request.initial_message.content == [{"type": "text", "text": "hello"}]
