import pytest

from beyo_manager.domain.app_update_presentations.composition_schemas import (
    validate_animation,
    validate_background_color,
    validate_layout,
    validate_style,
)
from beyo_manager.errors.validation import ValidationError


@pytest.mark.unit
def test_layout_accepts_normalized():
    out = validate_layout({"x": 0.1, "y": 0.7, "width": 0.8, "height": 0.2, "fit": "cover"})
    assert out == {"x": 0.1, "y": 0.7, "width": 0.8, "height": 0.2, "fit": "cover"}


@pytest.mark.unit
def test_layout_none_passthrough():
    assert validate_layout(None) is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [
        {"x": 1.5, "y": 0, "width": 1, "height": 1},   # x out of range
        {"x": 0, "y": 0, "width": 0, "height": 1},      # width must be > 0
        {"x": 0, "y": 0, "width": 1, "height": 1, "fit": "squish"},  # bad enum
        {"x": 0, "y": 0, "width": 1, "height": 1, "bogus": 1},        # extra forbidden
    ],
)
def test_layout_rejects_bad(bad):
    with pytest.raises(ValidationError):
        validate_layout(bad)


@pytest.mark.unit
def test_animation_accepts_known():
    out = validate_animation({"type": "fade_up", "duration_ms": 350, "easing": "ease_out"})
    assert out["type"] == "fade_up"


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [
        {"type": "explode"},                       # unknown type
        {"type": "fade", "duration_ms": 999999},   # too long
        {"type": "fade", "opacity": 5},            # out of range
        {"type": "fade", "bogus": 1},              # extra forbidden
        {"duration_ms": 100},                      # missing required type
    ],
)
def test_animation_rejects_bad(bad):
    with pytest.raises(ValidationError):
        validate_animation(bad)


@pytest.mark.unit
def test_style_hex_color_validation():
    out = validate_style({"text_role": "headline", "text_color": "#FFAA00"})
    assert out["text_color"] == "#FFAA00"
    with pytest.raises(ValidationError):
        validate_style({"text_color": "red"})


@pytest.mark.unit
@pytest.mark.parametrize("value", ["#FFAA00", "#102A43CC", None])
def test_background_color_accepts_hex_or_none(value):
    assert validate_background_color(value) == value


@pytest.mark.unit
@pytest.mark.parametrize("value", ["red", "#FFF", "#GGGGGG"])
def test_background_color_rejects_invalid_hex(value):
    with pytest.raises(ValidationError):
        validate_background_color(value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [
        {"text_role": "banner"},        # unknown role
        {"font_weight": 250},           # not a step of 100
        {"max_lines": 0},               # below min
        {"overflow": "wrap"},           # unknown
        {"unknown_key": 1},             # extra forbidden
    ],
)
def test_style_rejects_bad(bad):
    with pytest.raises(ValidationError):
        validate_style(bad)
