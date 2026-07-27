"""Validated JSON config schemas for slide timeline elements.

Layout, style, and animation are stored as JSONB but validated here as structured
Pydantic models — never free-form CSS. One slide-level
``composition_schema_version`` governs the interpretation of all three; the
frontend selects its renderer/adapter by that version.
"""

import re

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError as PydanticValidationError,
    field_validator,
)

from beyo_manager.domain.app_update_presentations.enums import (
    AnimationTypeEnum,
    EasingEnum,
    LayoutAnchorEnum,
    MediaFitEnum,
    TextAlignEnum,
    TextRoleEnum,
)
from beyo_manager.errors.validation import ValidationError

CURRENT_COMPOSITION_SCHEMA_VERSION = 1

_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _hex_color(value: str | None) -> str | None:
    if value is None:
        return value
    if not _HEX_COLOR.match(value):
        raise ValueError("must be a hex color like '#RRGGBB' or '#RRGGBBAA'.")
    return value


def validate_background_color(value: str | None) -> str | None:
    if value is None:
        return None
    if not _HEX_COLOR.match(value):
        raise ValidationError(
            "background_color must be a hex color like '#RRGGBB' or '#RRGGBBAA'."
        )
    return value


class LayoutConfig(BaseModel):
    """Normalized (0..1) placement so one composition renders across screen sizes."""

    model_config = ConfigDict(extra="forbid")

    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    anchor: LayoutAnchorEnum | None = None
    align: TextAlignEnum | None = None
    fit: MediaFitEnum | None = None
    rotation_deg: float | None = None
    scale: float | None = None

    @field_validator("x", "y")
    @classmethod
    def _pos_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("must be a normalized value between 0 and 1.")
        return v

    @field_validator("width", "height")
    @classmethod
    def _size_range(cls, v: float) -> float:
        if not 0.0 < v <= 1.0:
            raise ValueError("must be a normalized value in (0, 1].")
        return v

    @field_validator("rotation_deg")
    @classmethod
    def _rotation_range(cls, v: float | None) -> float | None:
        if v is not None and not -360.0 <= v <= 360.0:
            raise ValueError("must be between -360 and 360 degrees.")
        return v

    @field_validator("scale")
    @classmethod
    def _scale_range(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 < v <= 10.0:
            raise ValueError("must be in (0, 10].")
        return v


class TextStyleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_role: TextRoleEnum | None = None
    text_align: TextAlignEnum | None = None
    font_size: int | None = None
    font_weight: int | None = None
    text_color: str | None = None
    background_color: str | None = None
    border_radius: int | None = None
    padding: int | None = None
    max_lines: int | None = None
    overflow: str | None = None

    @field_validator("text_color", "background_color")
    @classmethod
    def _color(cls, v: str | None) -> str | None:
        return _hex_color(v)

    @field_validator("font_size")
    @classmethod
    def _font_size(cls, v: int | None) -> int | None:
        if v is not None and not 8 <= v <= 200:
            raise ValueError("font_size must be between 8 and 200.")
        return v

    @field_validator("font_weight")
    @classmethod
    def _font_weight(cls, v: int | None) -> int | None:
        if v is not None and v not in range(100, 1000, 100):
            raise ValueError("font_weight must be one of 100..900 (steps of 100).")
        return v

    @field_validator("border_radius", "padding")
    @classmethod
    def _non_negative_bounded(cls, v: int | None) -> int | None:
        if v is not None and not 0 <= v <= 400:
            raise ValueError("must be between 0 and 400.")
        return v

    @field_validator("max_lines")
    @classmethod
    def _max_lines(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 50:
            raise ValueError("max_lines must be between 1 and 50.")
        return v

    @field_validator("overflow")
    @classmethod
    def _overflow(cls, v: str | None) -> str | None:
        if v is not None and v not in {"clip", "ellipsis", "visible"}:
            raise ValueError("overflow must be 'clip', 'ellipsis', or 'visible'.")
        return v


class AnimationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AnimationTypeEnum
    duration_ms: int = 300
    delay_ms: int | None = None
    easing: EasingEnum | None = None
    distance: float | None = None
    scale: float | None = None
    opacity: float | None = None

    @field_validator("duration_ms", "delay_ms")
    @classmethod
    def _time_bound(cls, v: int | None) -> int | None:
        if v is not None and not 0 <= v <= 60000:
            raise ValueError("must be between 0 and 60000 ms.")
        return v

    @field_validator("distance", "opacity")
    @classmethod
    def _unit_range(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("must be a normalized value between 0 and 1.")
        return v

    @field_validator("scale")
    @classmethod
    def _scale_range(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 10.0:
            raise ValueError("must be in [0, 10].")
        return v


def _validate(model: type[BaseModel], data: dict | None, label: str) -> dict | None:
    if data is None:
        return None
    try:
        parsed = model.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{label}.{field}: {first['msg']}") from exc
    return parsed.model_dump(mode="json", exclude_none=True)


def validate_layout(data: dict | None) -> dict | None:
    return _validate(LayoutConfig, data, "layout")


def validate_style(data: dict | None) -> dict | None:
    return _validate(TextStyleConfig, data, "style")


def validate_animation(data: dict | None) -> dict | None:
    return _validate(AnimationConfig, data, "animation")
