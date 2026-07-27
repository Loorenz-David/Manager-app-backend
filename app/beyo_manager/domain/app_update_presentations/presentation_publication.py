"""Publication validation. Pure, no I/O.

Callers load the presentation graph, normalize slide/media sequences, then pass
plain structures here. This keeps every publish precondition in one tested place.
"""

from dataclasses import dataclass, field
from datetime import datetime

from beyo_manager.domain.app_update_presentations.enums import (
    AppKeyEnum,
    AudienceModeEnum,
    SlideMediaTypeEnum,
)
from beyo_manager.domain.app_update_presentations.audience_rules import (
    validate_audience_mode,
)
from beyo_manager.domain.app_update_presentations.slide_order import (
    assert_contiguous_sequence,
)
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.validation import ValidationError

_SUPPORTED_MEDIA_TYPES = {t.value for t in SlideMediaTypeEnum}
_KNOWN_APP_KEYS = {a.value for a in AppKeyEnum}
_KNOWN_ROLE_KEYS = {r.value for r in RoleNameEnum}


@dataclass
class MediaForPublish:
    media_type: str
    storage_key: str
    sequence_order: int


@dataclass
class SlideForPublish:
    sequence_order: int
    title: str | None
    description: str | None
    media: list[MediaForPublish] = field(default_factory=list)
    element_count: int = 0


def _validate_media(slide_index: int, media: list[MediaForPublish]) -> None:
    for item in media:
        if item.media_type not in _SUPPORTED_MEDIA_TYPES:
            raise ValidationError(
                f"Slide {slide_index}: unsupported media_type '{item.media_type}'."
            )
        if not item.storage_key or not item.storage_key.strip():
            raise ValidationError(
                f"Slide {slide_index}: a media item is missing its storage reference."
            )
    if media:
        assert_contiguous_sequence([m.sequence_order for m in media])


def _slide_has_content(slide: SlideForPublish) -> bool:
    has_text = bool((slide.title or "").strip()) or bool((slide.description or "").strip())
    return bool(slide.media) or has_text or slide.element_count > 0


def validate_publishable(
    *,
    slides: list[SlideForPublish],
    starts_at: datetime | None,
    expires_at: datetime | None,
    audience_mode: AudienceModeEnum,
    user_target_count: int,
    app_keys: set[str],
    role_keys: set[str],
) -> None:
    if not slides:
        raise ValidationError("A presentation must have at least one slide to publish.")

    assert_contiguous_sequence([s.sequence_order for s in slides])

    for position, slide in enumerate(slides, start=1):
        if not _slide_has_content(slide):
            raise ValidationError(f"Slide {position} has no media or text content.")
        _validate_media(position, slide.media)

    if starts_at is not None and expires_at is not None and expires_at <= starts_at:
        raise ValidationError("expires_at must be later than starts_at.")

    unknown_apps = app_keys - _KNOWN_APP_KEYS
    if unknown_apps:
        raise ValidationError(f"Unknown app target(s): {sorted(unknown_apps)}.")

    unknown_roles = role_keys - _KNOWN_ROLE_KEYS
    if unknown_roles:
        raise ValidationError(f"Unknown role target(s): {sorted(unknown_roles)}.")

    validate_audience_mode(audience_mode, user_target_count)
