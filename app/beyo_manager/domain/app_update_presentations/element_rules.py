"""Pure validation for slide timeline elements. No I/O.

Timing semantics (documented contract, used by creation, validation,
serialization, and the frontend renderer):
- ``start_ms`` is when the entrance animation begins.
- ``end_ms`` is when the exit animation begins.
- ``end_ms = null`` means the element remains present until the slide timeline
  ends (``duration_ms`` for a timed slide, the video end for a media-driven
  slide, or until the user advances for a manual slide).
"""

from beyo_manager.domain.app_update_presentations.enums import SlideElementTypeEnum
from beyo_manager.errors.validation import ValidationError


def validate_element_timing(
    start_ms: int,
    end_ms: int | None,
    *,
    slide_duration_ms: int | None,
    index: int,
) -> None:
    if start_ms < 0:
        raise ValidationError(f"Element {index}: start_ms cannot be negative.")
    if end_ms is not None and end_ms <= start_ms:
        raise ValidationError(f"Element {index}: end_ms must be greater than start_ms.")
    # When the slide declares an explicit duration, timed elements must fit it.
    if slide_duration_ms is not None:
        if start_ms >= slide_duration_ms:
            raise ValidationError(
                f"Element {index}: start_ms must be before the slide duration "
                f"({slide_duration_ms} ms)."
            )
        if end_ms is not None and end_ms > slide_duration_ms:
            raise ValidationError(
                f"Element {index}: end_ms cannot exceed the slide duration "
                f"({slide_duration_ms} ms)."
            )


def validate_element_payload(
    element_type: SlideElementTypeEnum,
    *,
    media_id: str | None,
    text_content: str | None,
    index: int,
) -> None:
    """Element type determines which payload is required and forbids the other."""
    if element_type == SlideElementTypeEnum.MEDIA:
        if not media_id:
            raise ValidationError(f"Element {index}: a media element requires media_id.")
        if text_content is not None and text_content.strip():
            raise ValidationError(
                f"Element {index}: a media element must not carry text_content."
            )
    elif element_type == SlideElementTypeEnum.TEXT:
        if not text_content or not text_content.strip():
            raise ValidationError(
                f"Element {index}: a text element requires non-empty text_content."
            )
        if media_id:
            raise ValidationError(
                f"Element {index}: a text element must not reference media."
            )
