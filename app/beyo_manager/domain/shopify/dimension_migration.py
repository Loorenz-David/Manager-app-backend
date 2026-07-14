"""Pure parsing and decision logic for the Shopify dimension backfill."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

_DIMENSION_PATTERN = re.compile(
    r"^\s*(?P<number>[+]?(?:\d+(?:[.,]\d+)?|[.,]\d+))\s*(?P<unit>mm|cm|m)?\s*$",
    re.IGNORECASE,
)
_LEGACY_DIMENSION_LINE_PATTERN = re.compile(
    r"^(?P<label>height|width|depth|seat\s+height)\s*:\s*(?P<value>.+)$",
    re.IGNORECASE,
)

TARGET_KEYS = (
    "height_dimension",
    "width_dimension",
    "depth_dimension",
    "extensions_quantity",
    "extension_dimension",
)


@dataclass(frozen=True)
class ParsedDimension:
    value_cm: Decimal


@dataclass(frozen=True)
class ParsedInvalid:
    reason: str


@dataclass(frozen=True)
class ParsedMissing:
    """A source metafield was absent or present with no meaningful value."""


@dataclass(frozen=True)
class LegacyDimensionParseResult:
    values: dict[str, str]
    parsed_fields: dict[str, dict[str, Any]]
    malformed_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParsedWidthWithExtensions:
    base_cm: Decimal
    extension_quantity: int
    extension_cm: Decimal | None


@dataclass(frozen=True)
class MigrationConfig:
    overwrite_existing: bool = False
    strict_product: bool = True
    disallow_zero: bool = True
    target_limits: dict[str, tuple[Decimal | None, Decimal | None]] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductMigrationInput:
    gid: str
    title: str = ""
    handle: str = ""
    sku: str | None = None
    legacy_height: str | None = None
    legacy_width: str | None = None
    legacy_depth: str | None = None
    legacy_extension_quantity: str | None = None
    legacy_dimensions: str | None = None
    existing_extensions_quantity: str | None = None
    existing_targets: dict[str, str | None] = field(default_factory=dict)

    @property
    def product_gid(self) -> str:
        return self.gid


@dataclass(frozen=True)
class ProductMigrationDecision:
    product_gid: str
    title: str
    handle: str
    sku: str | None
    status: str
    field_actions: dict[str, str] = field(default_factory=dict)
    proposed_values: dict[str, str] = field(default_factory=dict)
    delete_keys: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    raw_values: dict[str, str | None] = field(default_factory=dict)

    @property
    def legacy_extension_quantity(self) -> str | None:
        return self.raw_values.get("legacy_extension_quantity")

    @property
    def existing_extensions_quantity(self) -> str | None:
        return self.raw_values.get("existing_extensions_quantity")

    @property
    def proposed_extensions_quantity(self) -> str | None:
        return self.proposed_values.get("extensions_quantity")

    @property
    def extensions_quantity_source(self) -> str | None:
        for reason in self.reasons:
            if reason.startswith("extensions_quantity_source:"):
                return reason.split(":", 1)[1]
        return None

    @property
    def quantity_source_conflict(self) -> bool:
        return "conflicting_quantity_sources" in self.reasons

    @property
    def actions(self) -> dict[str, str]:
        return self.field_actions

    @property
    def overall_status(self) -> str:
        return self.status

    @property
    def action(self) -> str:
        """Stable operator-facing action label used by dry-run reports."""
        if self.status == "invalid":
            return "rejected"
        if self.status == "conflicting_target":
            return "skipped_existing"
        if self.status == "already_correct":
            return "unchanged"
        if any(action == "overwritten" for action in self.field_actions.values()):
            return "overwritten"
        if self.status == "proposed":
            return "created"
        return "skipped"

    @property
    def proposed_mutations(self) -> dict[str, str]:
        return self.proposed_values

    @property
    def is_invalid(self) -> bool:
        return self.status == "invalid"


@dataclass
class MigrationSummary:
    proposed: int = 0
    written: int = 0
    verified: int = 0
    already_correct: int = 0
    no_legacy_value: int = 0
    skipped: int = 0
    invalid: int = 0
    conflicting_target: int = 0
    mutation_failed: int = 0
    verification_failed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "proposed": self.proposed,
            "written": self.written,
            "verified": self.verified,
            "already_correct": self.already_correct,
            "no_legacy_value": self.no_legacy_value,
            "skipped": self.skipped,
            "invalid": self.invalid,
            "conflicting_target": self.conflicting_target,
            "mutation_failed": self.mutation_failed,
            "verification_failed": self.verification_failed,
        }


def parse_dimension_to_centimeters(
    raw: str | None,
    *,
    min_cm: Decimal | None = None,
    max_cm: Decimal | None = None,
    disallow_zero: bool = True,
) -> ParsedDimension | ParsedInvalid | ParsedMissing:
    if raw is None or not raw.strip():
        return ParsedMissing()

    match = _DIMENSION_PATTERN.fullmatch(raw)
    if match is None:
        return ParsedInvalid("unparseable_dimension")

    try:
        value = Decimal(match.group("number").replace(",", "."))
    except InvalidOperation:
        return ParsedInvalid("unparseable_dimension")
    if value < 0:
        return ParsedInvalid("negative_dimension")
    if value == 0 and disallow_zero:
        return ParsedInvalid("zero_dimension")

    unit = (match.group("unit") or "cm").lower()
    multiplier = {"mm": Decimal("0.1"), "cm": Decimal("1"), "m": Decimal("100")}[unit]
    value_cm = value * multiplier
    if min_cm is not None and value_cm < min_cm:
        return ParsedInvalid("below_minimum")
    if max_cm is not None and value_cm > max_cm:
        return ParsedInvalid("above_maximum")
    return ParsedDimension(value_cm=value_cm)


def parse_legacy_dimensions(raw: str | None) -> LegacyDimensionParseResult:
    """Parse legacy multiline dimensions while isolating malformed lines."""
    if raw is None or not raw.strip():
        return LegacyDimensionParseResult({}, {})
    labels = {"height": "height", "width": "width", "depth": "depth", "seat height": "seat_height"}
    values: dict[str, str] = {}
    parsed_fields: dict[str, dict[str, Any]] = {}
    malformed_lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _LEGACY_DIMENSION_LINE_PATTERN.fullmatch(stripped)
        if match is None:
            malformed_lines.append(stripped)
            continue
        field = labels[re.sub(r"\s+", " ", match.group("label").strip().lower())]
        dimension_raw = match.group("value").strip()
        if field == "width":
            parsed_width = parse_width_and_extensions(dimension_raw)
            if not isinstance(parsed_width, ParsedWidthWithExtensions):
                malformed_lines.append(stripped)
                continue
            dimension_for_metadata = dimension_raw.split("+", 1)[0].strip()
        else:
            parsed_dimension = parse_dimension_to_centimeters(dimension_raw)
            if not isinstance(parsed_dimension, ParsedDimension):
                malformed_lines.append(stripped)
                continue
            dimension_for_metadata = dimension_raw
        value_match = _DIMENSION_PATTERN.fullmatch(dimension_for_metadata)
        assert value_match is not None
        values[field] = dimension_raw
        parsed_fields[field] = {
            "value": Decimal(value_match.group("number").replace(",", ".")),
            "unit": (value_match.group("unit") or "cm").lower(),
        }
        if field == "width" and parsed_width.extension_quantity:
            parsed_fields[field].update({
                "extension_quantity": parsed_width.extension_quantity,
                "extension_value_cm": parsed_width.extension_cm,
            })
    return LegacyDimensionParseResult(values, parsed_fields, tuple(malformed_lines))


def parse_width_and_extensions(
    raw: str | None,
    *,
    min_cm: Decimal | None = None,
    max_cm: Decimal | None = None,
    disallow_zero: bool = True,
) -> ParsedWidthWithExtensions | ParsedInvalid | ParsedMissing:
    if raw is None or not raw.strip():
        return ParsedMissing()
    parts = [part.strip() for part in raw.split("+")]
    if not parts or any(not part for part in parts):
        return ParsedInvalid("unparseable_dimension")

    parsed = [
        parse_dimension_to_centimeters(
            part,
            min_cm=min_cm,
            max_cm=max_cm,
            disallow_zero=disallow_zero,
        )
        for part in parts
    ]
    if any(isinstance(item, ParsedInvalid) for item in parsed):
        first_invalid = next(item for item in parsed if isinstance(item, ParsedInvalid))
        return first_invalid
    if any(isinstance(item, ParsedMissing) for item in parsed):
        return ParsedInvalid("unparseable_dimension")

    dimensions = [item.value_cm for item in parsed if isinstance(item, ParsedDimension)]
    extension_values = dimensions[1:]
    if extension_values:
        most_common = Counter(extension_values).most_common()
        if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
            return ParsedInvalid("no_unique_common_extension_dimension")
        extension_cm = most_common[0][0]
    else:
        extension_cm = None
    return ParsedWidthWithExtensions(
        base_cm=dimensions[0],
        extension_quantity=len(extension_values),
        extension_cm=extension_cm,
    )


def serialize_shopify_dimension(value_cm: Decimal) -> str:
    numeric_value: int | float
    if value_cm == value_cm.to_integral_value():
        numeric_value = int(value_cm)
    else:
        numeric_value = float(value_cm)
    return json.dumps(
        {"value": numeric_value, "unit": "CENTIMETERS"},
        separators=(",", ":"),
    )


def serialize_shopify_integer(value: int) -> str:
    return str(value)


def build_product_migration(
    input: ProductMigrationInput,
    *,
    config: MigrationConfig,
) -> ProductMigrationDecision:
    legacy_dimensions = parse_legacy_dimensions(input.legacy_dimensions)
    legacy_values = legacy_dimensions.values
    height_result = _parse_target_dimension(
        legacy_values.get("height", legacy_values.get("seat_height", input.legacy_height)),
        "height_dimension",
        config,
    )
    width_result = parse_width_and_extensions(
        legacy_values.get("width", input.legacy_width),
        **_limits_for(config, "width_dimension"),
    )
    depth_result = _parse_target_dimension(legacy_values.get("depth", input.legacy_depth), "depth_dimension", config)
    results: dict[str, Any] = {
        "height_dimension": height_result,
        "width": width_result,
        "depth_dimension": depth_result,
    }
    raw_values = {
        "height": input.legacy_height,
        "width": input.legacy_width,
        "depth": input.legacy_depth,
        "legacy_dimensions": input.legacy_dimensions,
        "parsed_legacy_dimensions": legacy_dimensions.parsed_fields,
        "malformed_legacy_lines": legacy_dimensions.malformed_lines,
        "legacy_extension_quantity": input.legacy_extension_quantity,
        "existing_extensions_quantity": input.existing_extensions_quantity,
    }

    legacy_quantity_result = parse_legacy_extension_quantity(input.legacy_extension_quantity)
    existing_extensions_quantity = (
        input.existing_extensions_quantity
        if input.existing_extensions_quantity is not None
        else input.existing_targets.get("extensions_quantity")
    )
    results["legacy_extension_quantity"] = legacy_quantity_result

    invalid_reasons = []
    for field_name, result in results.items():
        if isinstance(result, ParsedInvalid):
            invalid_reasons.append(f"{field_name}:{result.reason}")
    if invalid_reasons and config.strict_product:
        return ProductMigrationDecision(
            product_gid=input.gid,
            title=input.title,
            handle=input.handle,
            sku=input.sku,
            status="invalid",
            field_actions={
                key: "rejected"
                for key, value in results.items()
                if not isinstance(value, ParsedMissing)
            },
            reasons=tuple(invalid_reasons),
            raw_values=raw_values,
        )

    field_actions: dict[str, str] = {}
    proposed_values: dict[str, str] = {}
    delete_keys: list[str] = []
    reasons = list(invalid_reasons)

    width_quantity: int | None = None
    if isinstance(width_result, ParsedWidthWithExtensions):
        width_quantity = width_result.extension_quantity
    legacy_quantity = legacy_quantity_result if isinstance(legacy_quantity_result, int) else None
    legacy_quantity_invalid = isinstance(legacy_quantity_result, ParsedInvalid)
    # A plain base width has the established zero-extension behavior, but is
    # not treated as a competing source when a legacy quantity is present.
    width_is_source = not legacy_quantity_invalid and width_quantity is not None and (
        width_quantity > 0 or legacy_quantity is None
    )
    if width_is_source and legacy_quantity is not None and width_quantity != legacy_quantity:
        reasons.append("conflicting_quantity_sources")
        field_actions["extensions_quantity"] = "source_conflict"
    elif width_is_source and legacy_quantity is not None:
        reasons.append("extensions_quantity_source:both_consistent")
    elif legacy_quantity is not None:
        reasons.append("extensions_quantity_source:legacy_extension_quantity")
    elif width_is_source:
        reasons.append("extensions_quantity_source:parsed_width")

    resolved_quantity: int | None = None
    if "conflicting_quantity_sources" not in reasons:
        if legacy_quantity is not None and not width_is_source:
            resolved_quantity = legacy_quantity
        elif width_is_source and legacy_quantity is not None:
            resolved_quantity = legacy_quantity
        elif width_is_source:
            resolved_quantity = width_quantity

    if isinstance(height_result, ParsedDimension):
        _add_value(
            "height_dimension",
            serialize_shopify_dimension(height_result.value_cm),
            input.existing_targets,
            config,
            field_actions,
            proposed_values,
            reasons,
        )
    if isinstance(width_result, ParsedWidthWithExtensions):
        _add_value(
            "width_dimension",
            serialize_shopify_dimension(width_result.base_cm),
            input.existing_targets,
            config,
            field_actions,
            proposed_values,
            reasons,
        )
        if resolved_quantity is not None:
            _add_value(
                "extensions_quantity",
                serialize_shopify_integer(resolved_quantity),
                {**input.existing_targets, "extensions_quantity": existing_extensions_quantity},
                config,
                field_actions,
                proposed_values,
                reasons,
            )
        if width_result.extension_cm is not None:
            _add_value(
                "extension_dimension",
                serialize_shopify_dimension(width_result.extension_cm),
                input.existing_targets,
                config,
                field_actions,
                proposed_values,
                reasons,
            )
        elif _has_value(input.existing_targets.get("extension_dimension")):
            if config.overwrite_existing:
                field_actions["extension_dimension"] = "delete_stale_extension"
                delete_keys.append("extension_dimension")
            else:
                field_actions["extension_dimension"] = "target_already_populated"
                reasons.append("extension_dimension:stale_existing_value")
    if isinstance(depth_result, ParsedDimension):
        _add_value(
            "depth_dimension",
            serialize_shopify_dimension(depth_result.value_cm),
            input.existing_targets,
            config,
            field_actions,
            proposed_values,
            reasons,
        )

    # A valid legacy quantity can be transferred even when width has no
    # extension components (or is missing in non-strict mode).
    if resolved_quantity is not None and "extensions_quantity" not in field_actions:
        _add_value(
            "extensions_quantity",
            serialize_shopify_integer(resolved_quantity),
            {**input.existing_targets, "extensions_quantity": existing_extensions_quantity},
            config, field_actions, proposed_values, reasons,
        )

    parsed_any = any(
        isinstance(result, (ParsedDimension, ParsedWidthWithExtensions))
        for result in results.values()
    ) or resolved_quantity is not None
    if not parsed_any:
        status = "invalid" if invalid_reasons else "no_legacy_value"
    elif any(action == "target_already_populated" for action in field_actions.values()):
        status = "conflicting_target"
    elif proposed_values or delete_keys:
        status = "proposed"
    elif any(action == "unchanged" for action in field_actions.values()):
        status = "already_correct"
    else:
        status = "skipped"

    return ProductMigrationDecision(
        product_gid=input.gid,
        title=input.title,
        handle=input.handle,
        sku=input.sku,
        status=status,
        field_actions=field_actions,
        proposed_values=proposed_values,
        delete_keys=tuple(delete_keys),
        reasons=tuple(reasons),
        raw_values=raw_values,
    )


def parse_legacy_extension_quantity(raw: str | None) -> int | ParsedInvalid | ParsedMissing:
    if raw is None or not raw.strip():
        return ParsedMissing()
    if not re.fullmatch(r"\s*\d+\s*", raw):
        return ParsedInvalid("invalid_extension_quantity")
    return int(raw.strip())


def _parse_target_dimension(
    raw: str | None,
    key: str,
    config: MigrationConfig,
) -> ParsedDimension | ParsedInvalid | ParsedMissing:
    return parse_dimension_to_centimeters(raw, **_limits_for(config, key))


def _limits_for(config: MigrationConfig, key: str) -> dict[str, Decimal | None | bool]:
    minimum, maximum = config.target_limits.get(key, (None, None))
    return {"min_cm": minimum, "max_cm": maximum, "disallow_zero": config.disallow_zero}


def _add_value(
    key: str,
    proposed: str,
    existing_targets: dict[str, str | None],
    config: MigrationConfig,
    actions: dict[str, str],
    proposed_values: dict[str, str],
    reasons: list[str],
) -> None:
    existing = existing_targets.get(key)
    if not _has_value(existing):
        actions[key] = "created"
        proposed_values[key] = proposed
    elif _values_equal(existing or "", proposed):
        actions[key] = "unchanged"
    elif config.overwrite_existing:
        actions[key] = "overwritten"
        proposed_values[key] = proposed
    else:
        actions[key] = "target_already_populated"
        reasons.append(f"{key}:existing_value_differs")


def _has_value(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _values_equal(left: str, right: str) -> bool:
    try:
        return json.loads(left) == json.loads(right)
    except (TypeError, ValueError, json.JSONDecodeError):
        return left.strip() == right.strip()
