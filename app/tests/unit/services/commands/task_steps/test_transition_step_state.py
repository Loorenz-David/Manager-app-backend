from types import SimpleNamespace

import pytest

from beyo_manager.services.commands.task_steps.transition_step_state import _resolve_transition_credit_user_id


@pytest.mark.unit
def test_transition_credit_defaults_to_actor():
    ctx = SimpleNamespace(user_id="usr_actor")
    request = SimpleNamespace(credited_user_id=None)

    assert _resolve_transition_credit_user_id(ctx, request) == "usr_actor"


@pytest.mark.unit
def test_transition_credit_uses_override_user():
    ctx = SimpleNamespace(user_id="usr_actor")
    request = SimpleNamespace(credited_user_id="usr_credit")

    assert _resolve_transition_credit_user_id(ctx, request) == "usr_credit"