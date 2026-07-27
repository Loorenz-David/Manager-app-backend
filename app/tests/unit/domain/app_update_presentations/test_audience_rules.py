import pytest

from beyo_manager.domain.app_update_presentations.audience_rules import (
    presentation_matches_context,
    validate_audience_mode,
)
from beyo_manager.domain.app_update_presentations.enums import AudienceModeEnum
from beyo_manager.errors.validation import ValidationError

ALL = AudienceModeEnum.ALL_MATCHING
SELECTED = AudienceModeEnum.SELECTED_USERS_ONLY


def _match(**overrides):
    base = dict(
        audience_mode=ALL,
        app_targets=set(),
        role_targets=set(),
        workspace_targets=set(),
        user_targets=set(),
        app_key="worker",
        workspace_id="ws_1",
        role_name="worker",
        user_id="usr_1",
    )
    base.update(overrides)
    return presentation_matches_context(**base)


@pytest.mark.unit
def test_validate_audience_mode_requires_users_for_selected():
    validate_audience_mode(ALL, 0)  # ok
    validate_audience_mode(SELECTED, 1)  # ok
    with pytest.raises(ValidationError):
        validate_audience_mode(SELECTED, 0)


@pytest.mark.unit
def test_empty_dimensions_are_unrestricted():
    assert _match() is True


@pytest.mark.unit
def test_or_within_app_dimension():
    assert _match(app_targets={"worker", "manager"}, app_key="manager") is True
    assert _match(app_targets={"manager", "seller"}, app_key="worker") is False


@pytest.mark.unit
def test_and_across_dimensions():
    # app matches but workspace does not -> overall no match
    assert (
        _match(app_targets={"worker"}, workspace_targets={"ws_other"}) is False
    )
    assert (
        _match(app_targets={"worker"}, workspace_targets={"ws_1"}) is True
    )


@pytest.mark.unit
def test_all_matching_role_dimension():
    assert _match(role_targets={"worker"}) is True
    assert _match(role_targets={"manager"}) is False


@pytest.mark.unit
def test_all_matching_direct_user_further_restricts():
    assert _match(user_targets={"usr_1"}) is True
    assert _match(user_targets={"usr_2"}) is False


@pytest.mark.unit
def test_selected_users_only_requires_direct_target():
    assert _match(audience_mode=SELECTED, user_targets={"usr_1"}) is True
    assert _match(audience_mode=SELECTED, user_targets={"usr_2"}) is False
    # empty user targets -> never matches in selected mode
    assert _match(audience_mode=SELECTED, user_targets=set()) is False


@pytest.mark.unit
def test_selected_users_only_ignores_role_targets():
    # role does not match, but user is directly targeted -> eligible
    assert (
        _match(
            audience_mode=SELECTED,
            user_targets={"usr_1"},
            role_targets={"manager"},
            role_name="worker",
        )
        is True
    )


@pytest.mark.unit
def test_selected_users_only_still_respects_app_and_workspace():
    assert (
        _match(
            audience_mode=SELECTED,
            user_targets={"usr_1"},
            app_targets={"manager"},
            app_key="worker",
        )
        is False
    )
