import pytest

from beyo_manager.domain.app_update_presentations.enums import (
    SlideElementTypeEnum,
    SlidePlaybackModeEnum,
)
from beyo_manager.domain.app_update_presentations.slide_timeline import (
    validate_slide_timeline,
)
from beyo_manager.errors.validation import ValidationError

MANUAL = SlidePlaybackModeEnum.MANUAL
TIMED = SlidePlaybackModeEnum.TIMED
MEDIA_DRIVEN = SlidePlaybackModeEnum.MEDIA_DRIVEN
MEDIA = SlideElementTypeEnum.MEDIA
TEXT = SlideElementTypeEnum.TEXT


@pytest.mark.unit
def test_timed_requires_duration():
    with pytest.raises(ValidationError):
        validate_slide_timeline(TIMED, None, [TEXT])
    validate_slide_timeline(TIMED, 5000, [TEXT])  # ok


@pytest.mark.unit
def test_media_driven_requires_media_element():
    with pytest.raises(ValidationError):
        validate_slide_timeline(MEDIA_DRIVEN, None, [TEXT])
    validate_slide_timeline(MEDIA_DRIVEN, None, [MEDIA, TEXT])  # ok


@pytest.mark.unit
def test_manual_needs_nothing():
    validate_slide_timeline(MANUAL, None, [])
    validate_slide_timeline(MANUAL, 3000, [TEXT])


@pytest.mark.unit
def test_non_positive_duration_rejected():
    with pytest.raises(ValidationError):
        validate_slide_timeline(MANUAL, 0, [TEXT])
    with pytest.raises(ValidationError):
        validate_slide_timeline(TIMED, -5, [TEXT])
