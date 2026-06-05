from beyo_manager.domain.images.enums import ImageAnnotationTypeEnum
from beyo_manager.errors.validation import ValidationError

_REQUIRED_KEYS = {
    ImageAnnotationTypeEnum.DRAW: {"points", "color"},
    ImageAnnotationTypeEnum.ARROW: {"from", "to"},
    ImageAnnotationTypeEnum.CIRCLE: {"cx", "cy", "r"},
    ImageAnnotationTypeEnum.RECTANGLE: {"x", "y", "w", "h"},
    ImageAnnotationTypeEnum.TEXT: {"x", "y", "text"},
    ImageAnnotationTypeEnum.MEASUREMENT: {"from", "to", "unit", "value"},
    ImageAnnotationTypeEnum.HIGHLIGHT: {"x", "y", "w", "h"},
}

_ANNOTATION_TYPE_VALUES = ", ".join(sorted(annotation_type.value for annotation_type in ImageAnnotationTypeEnum))


def parse_annotation_type(raw_value: str | None, *, field_name: str) -> ImageAnnotationTypeEnum:
    if not raw_value:
        raise ValidationError(f"{field_name} is required")
    try:
        return ImageAnnotationTypeEnum(raw_value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be one of: {_ANNOTATION_TYPE_VALUES}") from exc


def validate_payload_for_type(annotation_type: ImageAnnotationTypeEnum, payload: dict, *, prefix: str = "") -> None:
    missing = _REQUIRED_KEYS.get(annotation_type, set()) - payload.keys()
    if missing:
        raise ValidationError(f"{prefix}missing required keys for {annotation_type.value}: {sorted(missing)}")


def normalize_payload_for_type(annotation_type: ImageAnnotationTypeEnum, payload: dict) -> dict:
    # Frontend arrow drawings may send scalar endpoints instead of nested points.
    # Normalize to backend canonical keys while preserving original fields.
    if annotation_type == ImageAnnotationTypeEnum.ARROW:
        normalized = dict(payload)
        if "from" not in normalized and {"fromX", "fromY"}.issubset(normalized.keys()):
            normalized["from"] = {"x": normalized["fromX"], "y": normalized["fromY"]}
        if "to" not in normalized and {"toX", "toY"}.issubset(normalized.keys()):
            normalized["to"] = {"x": normalized["toX"], "y": normalized["toY"]}
        return normalized
    return payload


def parse_annotation_items(items: list, *, prefix: str = "items") -> list[tuple[ImageAnnotationTypeEnum, dict, int | None]]:
    if not isinstance(items, list):
        raise ValidationError(f"{prefix} must be an array")
    if not items:
        raise ValidationError(f"{prefix} must not be empty")

    parsed: list[tuple[ImageAnnotationTypeEnum, dict, int | None]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationError(f"{prefix}[{index}] must be an object")
        # Accept canonical "annotation_type" or legacy "tool" alias.
        annotation_type_raw = item.get("annotation_type") or item.get("tool")
        annotation_type = parse_annotation_type(annotation_type_raw, field_name=f"{prefix}[{index}].annotation_type")
        normalized_item = normalize_payload_for_type(annotation_type, item)
        validate_payload_for_type(annotation_type, normalized_item, prefix=f"{prefix}[{index}] ")
        accuracy_raw = item.get("accuracy")
        accuracy: int | None = None
        if accuracy_raw is not None:
            if isinstance(accuracy_raw, bool) or not isinstance(accuracy_raw, int) or not (0 <= accuracy_raw <= 100):
                raise ValidationError(f"{prefix}[{index}].accuracy must be an integer 0–100")
            accuracy = accuracy_raw
        parsed.append((annotation_type, normalized_item, accuracy))
    return parsed
