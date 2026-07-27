"""Slide-level timeline / playback rules. Pure, no I/O."""

from beyo_manager.domain.app_update_presentations.enums import (
    SlideElementTypeEnum,
    SlidePlaybackModeEnum,
)
from beyo_manager.errors.validation import ValidationError


def validate_slide_timeline(
    playback_mode: SlidePlaybackModeEnum,
    duration_ms: int | None,
    element_types: list[SlideElementTypeEnum],
) -> None:
    if duration_ms is not None and duration_ms <= 0:
        raise ValidationError("duration_ms must be positive when set.")

    if playback_mode == SlidePlaybackModeEnum.TIMED and duration_ms is None:
        raise ValidationError("A 'timed' slide requires an explicit duration_ms.")

    if playback_mode == SlidePlaybackModeEnum.MEDIA_DRIVEN and not any(
        t == SlideElementTypeEnum.MEDIA for t in element_types
    ):
        raise ValidationError(
            "A 'media_driven' slide requires at least one media element."
        )
