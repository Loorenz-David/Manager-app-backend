from decimal import Decimal

import pytest

from beyo_manager.domain.shopify.dimension_migration import (
    MigrationConfig,
    ParsedDimension,
    ParsedInvalid,
    ParsedMissing,
    ProductMigrationInput,
    build_product_migration,
    parse_dimension_to_centimeters,
    parse_legacy_dimensions,
    parse_width_and_extensions,
    serialize_shopify_dimension,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("100", Decimal("100")), ("100cm", Decimal("100")), ("100 cm", Decimal("100")),
        ("100.5cm", Decimal("100.5")), ("100,5 cm", Decimal("100.5")),
        ("1m", Decimal("100")), ("500mm", Decimal("50")),
    ],
)
def test_dimension_parser_normalizes_to_centimeters(raw, expected) -> None:
    result = parse_dimension_to_centimeters(raw)
    assert isinstance(result, ParsedDimension)
    assert result.value_cm == expected


@pytest.mark.unit
def test_legacy_multiline_dimensions_parse_supported_fields_and_audit_bad_lines() -> None:
    result = parse_legacy_dimensions(
        "  Depth: 35 cm\n\n width : 49,5 cm\nHEIGHT: 43.5 cm\nSeat height: 44\nNot a dimension"
    )
    assert result.values == {
        "depth": "35 cm", "width": "49,5 cm", "height": "43.5 cm", "seat_height": "44",
    }
    assert result.parsed_fields["width"] == {"value": Decimal("49.5"), "unit": "cm"}
    assert result.parsed_fields["height"] == {"value": Decimal("43.5"), "unit": "cm"}
    assert result.parsed_fields["seat_height"] == {"value": Decimal("44"), "unit": "cm"}
    assert result.malformed_lines == ("Not a dimension",)


@pytest.mark.unit
def test_legacy_multiline_width_derives_extensions_from_compound_value() -> None:
    result = parse_legacy_dimensions("Width: 130 + 25 + 25 + 40 cm")
    assert result.values["width"] == "130 + 25 + 25 + 40 cm"
    assert result.parsed_fields["width"]["value"] == Decimal("130")
    assert result.parsed_fields["width"]["extension_quantity"] == 3
    assert result.parsed_fields["width"]["extension_value_cm"] == Decimal("25")

    decision = build_product_migration(
        _input(legacy_dimensions="Width: 130 + 25 + 25 + 40 cm"),
        config=MigrationConfig(),
    )
    assert decision.proposed_values["width_dimension"] == '{"value":130,"unit":"CENTIMETERS"}'
    assert decision.proposed_values["extensions_quantity"] == "3"
    assert decision.proposed_values["extension_dimension"] == '{"value":25,"unit":"CENTIMETERS"}'


@pytest.mark.unit
def test_legacy_seat_height_without_height_maps_without_zero_values() -> None:
    decision = build_product_migration(
        _input(legacy_dimensions="Depth: 45 cm\nWidth: 47 cm\nSeat height: 44 cm"),
        config=MigrationConfig(),
    )
    assert decision.proposed_values == {
        "depth_dimension": '{"value":45,"unit":"CENTIMETERS"}',
        "width_dimension": '{"value":47,"unit":"CENTIMETERS"}',
        "height_dimension": '{"value":44,"unit":"CENTIMETERS"}',
    }


@pytest.mark.unit
@pytest.mark.parametrize("raw", [None, "", "  "])
def test_empty_or_null_legacy_multiline_metafield_is_not_a_candidate(raw) -> None:
    decision = build_product_migration(_input(legacy_dimensions=raw), config=MigrationConfig())
    assert decision.status == "no_legacy_value"


@pytest.mark.unit
def test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values() -> None:
    existing = {"depth_dimension": '{"value":35,"unit":"CENTIMETERS"}'}
    decision = build_product_migration(
        _input(legacy_dimensions="Depth: 35 cm\nWidth: 49 cm", existing_targets=existing),
        config=MigrationConfig(),
    )
    assert decision.field_actions["depth_dimension"] == "unchanged"
    assert decision.proposed_values == {"width_dimension": '{"value":49,"unit":"CENTIMETERS"}'}


@pytest.mark.unit
@pytest.mark.parametrize("raw", [None, "", "  "])
def test_missing_dimension_is_distinct_from_invalid(raw) -> None:
    assert isinstance(parse_dimension_to_centimeters(raw), ParsedMissing)


@pytest.mark.unit
@pytest.mark.parametrize("raw", ["N/A", "100-120", "100 x 50", "100 + bad", "-5", "0"])
def test_invalid_dimension_is_never_guessed(raw) -> None:
    assert isinstance(parse_dimension_to_centimeters(raw), ParsedInvalid)


@pytest.mark.unit
def test_width_extensions_use_unique_most_common_extension_size() -> None:
    result = parse_width_and_extensions("100cm + 50cm + 40cm + 50cm")
    assert result.base_cm == Decimal("100")
    assert result.extension_quantity == 3
    assert result.extension_cm == Decimal("50")
    invalid = parse_width_and_extensions("100 + 50 + 40")
    assert isinstance(invalid, ParsedInvalid)
    assert invalid.reason == "no_unique_common_extension_dimension"


@pytest.mark.unit
def test_serialization_matches_shopify_scalars() -> None:
    assert serialize_shopify_dimension(Decimal("100")) == '{"value":100,"unit":"CENTIMETERS"}'
    assert serialize_shopify_dimension(Decimal("2.5")) == '{"value":2.5,"unit":"CENTIMETERS"}'


def _input(**kwargs) -> ProductMigrationInput:
    return ProductMigrationInput(gid="gid://shopify/Product/1", **kwargs)


@pytest.mark.unit
def test_target_protection_is_idempotent_and_overwrite_is_explicit() -> None:
    base = _input(legacy_height="100", existing_targets={})
    created = build_product_migration(base, config=MigrationConfig())
    assert created.field_actions["height_dimension"] == "created"
    assert created.proposed_values["height_dimension"] == '{"value":100,"unit":"CENTIMETERS"}'

    same = build_product_migration(
        _input(legacy_height="100", existing_targets=created.proposed_values),
        config=MigrationConfig(),
    )
    assert same.status == "already_correct"
    assert same.proposed_values == {}

    conflict = build_product_migration(
        _input(legacy_height="100", existing_targets={"height_dimension": '{"value":90,"unit":"CENTIMETERS"}'}),
        config=MigrationConfig(),
    )
    assert conflict.status == "conflicting_target"
    assert conflict.proposed_values == {}
    overwritten = build_product_migration(
        _input(legacy_height="100", existing_targets={"height_dimension": '{"value":90,"unit":"CENTIMETERS"}'}),
        config=MigrationConfig(overwrite_existing=True),
    )
    assert overwritten.field_actions["height_dimension"] == "overwritten"


@pytest.mark.unit
def test_missing_values_are_not_rejected_by_strict_mode() -> None:
    decision = build_product_migration(
        _input(legacy_height=None, legacy_width="100 + 50 + 40", legacy_depth=""),
        config=MigrationConfig(strict_product=True),
    )
    assert decision.status == "invalid"
    only_missing = build_product_migration(_input(), config=MigrationConfig(strict_product=True))
    assert only_missing.status == "no_legacy_value"


@pytest.mark.unit
def test_target_limits_are_applied_after_unit_conversion() -> None:
    result = parse_dimension_to_centimeters("2m", max_cm=Decimal("100"))
    assert isinstance(result, ParsedInvalid)
    assert result.reason == "above_maximum"


@pytest.mark.unit
def test_compound_width_targets_plural_quantity_key() -> None:
    decision = build_product_migration(
        _input(legacy_width="100cm + 50cm + 50cm"), config=MigrationConfig()
    )
    assert decision.proposed_values["extensions_quantity"] == "2"
    assert "extension_quantity" not in decision.proposed_values


@pytest.mark.unit
def test_legacy_quantity_transfers_to_canonical_target() -> None:
    decision = build_product_migration(
        _input(legacy_width="100cm", legacy_extension_quantity=" 2 "),
        config=MigrationConfig(),
    )
    assert decision.proposed_values["extensions_quantity"] == "2"
    assert decision.extensions_quantity_source == "legacy_extension_quantity"


@pytest.mark.unit
def test_canonical_quantity_is_protected_and_overwrite_is_explicit() -> None:
    conflicting = build_product_migration(
        _input(legacy_width="100cm", legacy_extension_quantity="2", existing_extensions_quantity="3"),
        config=MigrationConfig(),
    )
    assert conflicting.field_actions["extensions_quantity"] == "target_already_populated"
    assert "extensions_quantity" not in conflicting.proposed_values

    overwritten = build_product_migration(
        _input(legacy_width="100cm", legacy_extension_quantity="2", existing_extensions_quantity="3"),
        config=MigrationConfig(overwrite_existing=True),
    )
    assert overwritten.proposed_values["extensions_quantity"] == "2"


@pytest.mark.unit
def test_quantity_sources_agree_or_conflict_without_silent_preference() -> None:
    agree = build_product_migration(
        _input(legacy_width="100cm + 50cm + 50cm", legacy_extension_quantity="2"),
        config=MigrationConfig(),
    )
    assert agree.extensions_quantity_source == "both_consistent"
    assert agree.proposed_values["extensions_quantity"] == "2"

    conflict = build_product_migration(
        _input(legacy_width="100cm + 50cm + 50cm", legacy_extension_quantity="3"),
        config=MigrationConfig(),
    )
    assert conflict.quantity_source_conflict
    assert conflict.proposed_values.get("extensions_quantity") is None
    assert "conflicting_quantity_sources" in conflict.reasons


@pytest.mark.unit
@pytest.mark.parametrize("raw", ["two", "2.5", "-1", "2 extensions", "{\"value\":2}"])
def test_invalid_legacy_quantity_is_not_guessed(raw: str) -> None:
    decision = build_product_migration(
        _input(legacy_width="100cm", legacy_extension_quantity=raw),
        config=MigrationConfig(strict_product=False),
    )
    assert "legacy_extension_quantity:invalid_extension_quantity" in decision.reasons
    assert "extensions_quantity" not in decision.proposed_values


@pytest.mark.unit
def test_already_migrated_quantity_is_idempotent() -> None:
    decision = build_product_migration(
        _input(legacy_width="100cm", legacy_extension_quantity="2", existing_extensions_quantity="2",
               existing_targets={"width_dimension": '{"value":100,"unit":"CENTIMETERS"}'}),
        config=MigrationConfig(),
    )
    assert decision.field_actions["extensions_quantity"] == "unchanged"
    assert "extensions_quantity" not in decision.proposed_values
