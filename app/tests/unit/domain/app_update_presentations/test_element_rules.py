import pytest

from beyo_manager.domain.app_update_presentations.element_rules import (
    validate_element_payload,
    validate_element_timing,
)
from beyo_manager.domain.app_update_presentations.enums import SlideElementTypeEnum
from beyo_manager.errors.validation import ValidationError

MEDIA = SlideElementTypeEnum.MEDIA
TEXT = SlideElementTypeEnum.TEXT


@pytest.mark.unit
def test_timing_start_non_negative():
    with pytest.raises(ValidationError):
        validate_element_timing(-1, None, slide_duration_ms=None, index=0)


@pytest.mark.unit
def test_timing_end_after_start():
    with pytest.raises(ValidationError):
        validate_element_timing(1000, 1000, slide_duration_ms=None, index=0)
    validate_element_timing(1000, 2000, slide_duration_ms=None, index=0)  # ok


@pytest.mark.unit
def test_timing_null_end_is_allowed():
    validate_element_timing(0, None, slide_duration_ms=8000, index=0)


@pytest.mark.unit
def test_timing_within_slide_duration():
    validate_element_timing(0, 8000, slide_duration_ms=8000, index=0)  # ok
    with pytest.raises(ValidationError):
        validate_element_timing(8000, None, slide_duration_ms=8000, index=0)  # start == dur
    with pytest.raises(ValidationError):
        validate_element_timing(0, 9000, slide_duration_ms=8000, index=0)  # end > dur


@pytest.mark.unit
def test_media_payload_requires_media_id():
    with pytest.raises(ValidationError):
        validate_element_payload(MEDIA, media_id=None, text_content=None, index=0)
    validate_element_payload(MEDIA, media_id="aupm_1", text_content=None, index=0)


@pytest.mark.unit
def test_media_payload_forbids_text():
    with pytest.raises(ValidationError):
        validate_element_payload(MEDIA, media_id="aupm_1", text_content="hi", index=0)


@pytest.mark.unit
def test_text_payload_requires_text():
    with pytest.raises(ValidationError):
        validate_element_payload(TEXT, media_id=None, text_content="   ", index=0)
    validate_element_payload(TEXT, media_id=None, text_content="Hello", index=0)


@pytest.mark.unit
def test_text_payload_forbids_media():
    with pytest.raises(ValidationError):
        validate_element_payload(TEXT, media_id="aupm_1", text_content="Hi", index=0)
