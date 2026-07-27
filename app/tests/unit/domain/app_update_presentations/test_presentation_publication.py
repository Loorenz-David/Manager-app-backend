import pytest

from beyo_manager.domain.app_update_presentations.enums import AudienceModeEnum
from beyo_manager.domain.app_update_presentations.presentation_publication import (
    MediaForPublish,
    SlideForPublish,
    validate_publishable,
)
from beyo_manager.errors.validation import ValidationError

ALL = AudienceModeEnum.ALL_MATCHING
SELECTED = AudienceModeEnum.SELECTED_USERS_ONLY


def _slide(order, *, title="t", description="d", media=None):
    return SlideForPublish(
        sequence_order=order, title=title, description=description, media=media or []
    )


def _publish(**overrides):
    base = dict(
        slides=[_slide(1)],
        starts_at=None,
        expires_at=None,
        audience_mode=ALL,
        user_target_count=0,
        app_keys=set(),
        role_keys=set(),
    )
    base.update(overrides)
    return validate_publishable(**base)


@pytest.mark.unit
def test_valid_publish_passes():
    _publish()


@pytest.mark.unit
def test_requires_at_least_one_slide():
    with pytest.raises(ValidationError):
        _publish(slides=[])


@pytest.mark.unit
def test_slide_needs_content():
    with pytest.raises(ValidationError):
        _publish(slides=[_slide(1, title=None, description=None, media=[])])


@pytest.mark.unit
def test_slide_with_only_media_is_valid():
    media = [MediaForPublish(media_type="image", storage_key="k", sequence_order=1)]
    _publish(slides=[_slide(1, title=None, description=None, media=media)])


@pytest.mark.unit
def test_unsupported_media_type_rejected():
    media = [MediaForPublish(media_type="audio", storage_key="k", sequence_order=1)]
    with pytest.raises(ValidationError):
        _publish(slides=[_slide(1, media=media)])


@pytest.mark.unit
def test_media_missing_storage_key_rejected():
    media = [MediaForPublish(media_type="image", storage_key="", sequence_order=1)]
    with pytest.raises(ValidationError):
        _publish(slides=[_slide(1, media=media)])


@pytest.mark.unit
def test_non_contiguous_slides_rejected():
    with pytest.raises(ValidationError):
        _publish(slides=[_slide(1), _slide(3)])


@pytest.mark.unit
def test_expiry_must_be_after_start():
    from datetime import datetime, timedelta, timezone

    start = datetime(2026, 7, 21, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        _publish(starts_at=start, expires_at=start - timedelta(hours=1))


@pytest.mark.unit
def test_unknown_app_key_rejected():
    with pytest.raises(ValidationError):
        _publish(app_keys={"managerz"})


@pytest.mark.unit
def test_unknown_role_key_rejected():
    with pytest.raises(ValidationError):
        _publish(role_keys={"superuser"})


@pytest.mark.unit
def test_selected_users_only_requires_user_target():
    with pytest.raises(ValidationError):
        _publish(audience_mode=SELECTED, user_target_count=0)
    _publish(audience_mode=SELECTED, user_target_count=1)
