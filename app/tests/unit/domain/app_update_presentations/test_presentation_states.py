import pytest

from beyo_manager.domain.app_update_presentations.enums import PresentationStatusEnum
from beyo_manager.domain.app_update_presentations.presentation_states import (
    assert_presentation_is_draft,
    assert_valid_status_transition,
)
from beyo_manager.errors.validation import ConflictError

DRAFT = PresentationStatusEnum.DRAFT
PUBLISHED = PresentationStatusEnum.PUBLISHED
ARCHIVED = PresentationStatusEnum.ARCHIVED


@pytest.mark.unit
@pytest.mark.parametrize("target", [PUBLISHED, ARCHIVED])
def test_draft_can_publish_or_archive(target):
    assert_valid_status_transition(DRAFT, target)  # does not raise


@pytest.mark.unit
def test_published_can_only_archive():
    assert_valid_status_transition(PUBLISHED, ARCHIVED)
    with pytest.raises(ConflictError):
        assert_valid_status_transition(PUBLISHED, PUBLISHED)
    with pytest.raises(ConflictError):
        assert_valid_status_transition(PUBLISHED, DRAFT)


@pytest.mark.unit
@pytest.mark.parametrize("target", [DRAFT, PUBLISHED, ARCHIVED])
def test_archived_is_terminal(target):
    with pytest.raises(ConflictError):
        assert_valid_status_transition(ARCHIVED, target)


@pytest.mark.unit
def test_assert_presentation_is_draft():
    assert_presentation_is_draft(DRAFT)
    with pytest.raises(ConflictError):
        assert_presentation_is_draft(PUBLISHED)
    with pytest.raises(ConflictError):
        assert_presentation_is_draft(ARCHIVED)
