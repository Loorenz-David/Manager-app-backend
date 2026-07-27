import pytest

from beyo_manager.domain.app_update_presentations.enums import (
    PresentationViewStatusEnum,
)
from beyo_manager.domain.app_update_presentations.view_state_rules import (
    DISMISSED,
    assert_dismiss_allowed,
    assert_no_completion_regression,
    assert_valid_action,
    validate_slide_index,
)
from beyo_manager.errors.validation import ConflictError, ValidationError

COMPLETED = PresentationViewStatusEnum.COMPLETED
SHOWN = PresentationViewStatusEnum.SHOWN


@pytest.mark.unit
def test_valid_actions():
    for action in ("shown", "progressed", "dismissed", "completed"):
        assert_valid_action(action)


@pytest.mark.unit
def test_invalid_action_rejected():
    with pytest.raises(ValidationError):
        assert_valid_action("exploded")


@pytest.mark.unit
def test_dismiss_requires_dismissible():
    assert_dismiss_allowed(True)
    with pytest.raises(ConflictError):
        assert_dismiss_allowed(False)


@pytest.mark.unit
def test_completed_cannot_be_dismissed():
    with pytest.raises(ConflictError):
        assert_no_completion_regression(COMPLETED, DISMISSED)


@pytest.mark.unit
def test_non_completed_can_be_dismissed():
    assert_no_completion_regression(SHOWN, DISMISSED)  # does not raise


@pytest.mark.unit
def test_slide_index_bounds():
    validate_slide_index(0, 3)
    validate_slide_index(2, 3)
    with pytest.raises(ValidationError):
        validate_slide_index(3, 3)
    with pytest.raises(ValidationError):
        validate_slide_index(-1, 3)


@pytest.mark.unit
def test_slide_index_zero_slides():
    validate_slide_index(0, 0)
    with pytest.raises(ValidationError):
        validate_slide_index(1, 0)
