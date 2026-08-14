from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.services.commands.item_economics._common import translate_integrity_error
from beyo_manager.services.commands.item_economics.requests import (
    parse_cost_model_version_create_request,
    parse_item_valuation_request,
    parse_production_cost_group_create_request,
    parse_production_cost_group_update_request,
    parse_production_cost_basis_version_create_request,
)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Main"},
        {"name": "Main", "major_category": "metal"},
        {"name": "Main", "major_category": "WOOD"},
    ],
    ids=["missing-category", "unknown-category", "wrong-case-category"],
)
def test_group_create_request_rejects_missing_and_non_vocabulary_categories(payload):
    with pytest.raises(ValidationError, match="major_category"):
        parse_production_cost_group_create_request(payload)


def test_group_requests_use_lowercase_enum_values_and_accept_explicit_update_null():
    created = parse_production_cost_group_create_request({"name": "Main", "major_category": "wood"})
    updated = parse_production_cost_group_update_request({"client_id": "pcg_1", "name": "Main", "major_category": None})

    assert created.major_category.value == "wood"
    assert updated.major_category is None


def test_basis_request_canonicalizes_numeric_columns_before_command_derivation():
    request = parse_production_cost_basis_version_create_request(
        {
            "production_cost_group_id": "pcg_1",
            "fixed_monthly_cost_minor": 100000,
            "currency": "swedish_krona",
            "monthly_paid_hours": 173.456,
            "planning_utilization_percent": 80.00,
            "cost_per_worker_minute_minor": 999,
        }
    )
    assert request.monthly_paid_hours == Decimal("173.46")
    assert request.planning_utilization_percent == Decimal("80.00")


def test_basis_request_parses_float_as_decimal_text_before_quantization():
    request = parse_production_cost_basis_version_create_request(
        {
            "production_cost_group_id": "pcg_1",
            "fixed_monthly_cost_minor": 100000,
            "currency": "swedish_krona",
            "monthly_paid_hours": 2.675,
            "planning_utilization_percent": 80,
        }
    )

    assert request.monthly_paid_hours == Decimal("2.68")


def test_model_request_canonicalizes_percentage_terms_to_three_places():
    request = parse_cost_model_version_create_request(
        {
            "currency": "swedish_krona",
            "terms": [{"name": "allocation", "calculation_type": "percentage_of_expected_sale_price", "percent_value": 12.01056}],
        }
    )
    assert request.terms[0].percent_value == Decimal("12.011")


@pytest.mark.parametrize(
    ("index_name", "identity"),
    [
        ("uix_production_cost_groups_name_active", "ITEM_COST_GROUP_NAME_TAKEN"),
        ("uix_production_cost_groups_major_category_active", "ITEM_COST_GROUP_CATEGORY_TAKEN"),
        ("uix_production_cost_group_sections_active", "ITEM_COST_SECTION_ALREADY_GROUPED"),
        ("uix_production_cost_basis_versions_open", "ITEM_COST_CONCURRENT_BASIS_VERSION"),
        ("uix_cost_model_versions_open", "ITEM_COST_CONCURRENT_MODEL_VERSION"),
        ("uix_cost_model_terms_purchase_cost", "ITEM_COST_PURCHASE_TERM_DUPLICATE"),
        ("uix_cost_model_terms_name_active", "ITEM_COST_TERM_NAME_TAKEN"),
        ("uix_item_valuations_current", "ITEM_COST_CONCURRENT_VALUATION"),
        ("uix_item_cost_evaluations_current", "ITEM_COST_CONCURRENT_COMMIT"),
    ],
)
def test_integrity_translation_preserves_each_registered_index_identity(index_name, identity):
    known = IntegrityError(None, None, Exception(f"duplicate key {index_name}"))
    with pytest.raises(ConflictError, match=f"^{identity}:"):
        translate_integrity_error(known)


def test_integrity_translation_preserves_unknown_paths():
    unknown = IntegrityError(None, None, Exception("database connection failed"))
    with pytest.raises(IntegrityError) as raised:
        translate_integrity_error(unknown)
    assert raised.value is unknown


def test_valuation_request_requires_at_least_one_amount_after_pydantic_parse():
    with pytest.raises(ValidationError, match=r"^ITEM_COST_VALUATION_AMOUNT_REQUIRED:"):
        parse_item_valuation_request({"currency": "swedish_krona"})


def test_valuation_request_rejects_missing_currency_at_request_layer():
    with pytest.raises(ValidationError, match="currency"):
        parse_item_valuation_request({"expected_sale_price_minor": 100})


@pytest.mark.parametrize(
    "payload",
    [
        {"expected_sale_price_minor": 100, "currency": "swedish_krona"},
        {"purchase_cost_minor": 50, "currency": "swedish_krona"},
        {"expected_sale_price_minor": 100, "purchase_cost_minor": 50, "currency": "swedish_krona"},
    ],
    ids=["expected-only", "cost-only", "both"],
)
def test_valuation_request_accepts_each_amount_shape(payload):
    request = parse_item_valuation_request(payload)

    assert request.currency.value == "swedish_krona"


# Phase 2 DB-CHECK authority for the six request-layer companion rows:
# node:table-item-valuation (negative expected, negative purchase, both-null,
# price-only, cost-only, and NULL currency).


@pytest.mark.parametrize(
    ("field", "value"),
    [("expected_sale_price_minor", -1), ("purchase_cost_minor", -1)],
    ids=["negative-expected", "negative-purchase"],
)
def test_valuation_request_rejects_each_negative_amount_at_request_layer(field, value):
    with pytest.raises(ValidationError, match=field):
        parse_item_valuation_request({"currency": "swedish_krona", field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fixed_monthly_cost_minor", 0),
        ("monthly_paid_hours", -5),
        ("monthly_paid_hours", 0),
        ("planning_utilization_percent", 0),
        ("planning_utilization_percent", 100.01),
    ],
    ids=["fixed-zero", "hours-negative", "hours-zero", "util-zero", "util-over-100"],
)
def test_basis_request_rejects_each_out_of_range_numeric_field(field, value):
    payload = {
        "production_cost_group_id": "pcg_1",
        "fixed_monthly_cost_minor": 100000,
        "currency": "swedish_krona",
        "monthly_paid_hours": 160,
        "planning_utilization_percent": 80,
    }
    payload[field] = value

    with pytest.raises(ValidationError, match=field):
        parse_production_cost_basis_version_create_request(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("percent_value", -1), ("percent_value", 1000), ("fixed_amount_minor", -5)],
    ids=["percent-negative", "percent-over-numeric-bound", "fixed-negative"],
)
def test_term_request_rejects_each_out_of_range_numeric_field(field, value):
    term = {
        "name": "allocation",
        "calculation_type": "percentage_of_expected_sale_price",
        "percent_value": 10,
    }
    term[field] = value

    with pytest.raises(ValidationError, match=field):
        parse_cost_model_version_create_request({"currency": "swedish_krona", "terms": [term]})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fixed_monthly_cost_minor", 1),
        ("monthly_paid_hours", 1),
        ("planning_utilization_percent", 100),
    ],
    ids=["fixed-one", "hours-one", "util-one-hundred"],
)
def test_basis_request_accepts_each_included_numeric_boundary(field, value):
    payload = {
        "production_cost_group_id": "pcg_1",
        "fixed_monthly_cost_minor": 1,
        "currency": "swedish_krona",
        "monthly_paid_hours": 1,
        "planning_utilization_percent": 100,
    }
    payload[field] = value

    assert parse_production_cost_basis_version_create_request(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("percent_value", 0), ("percent_value", 999.999), ("fixed_amount_minor", 0)],
    ids=["percent-zero", "percent-max", "fixed-amount-zero"],
)
def test_term_request_accepts_each_included_numeric_boundary(field, value):
    calculation_type = "fixed_amount" if field == "fixed_amount_minor" else "percentage_of_expected_sale_price"
    term = {
        "name": "allocation",
        "calculation_type": calculation_type,
        "percent_value": 10 if calculation_type == "percentage_of_expected_sale_price" else None,
        "fixed_amount_minor": 0 if calculation_type == "fixed_amount" else None,
    }
    term[field] = value

    assert parse_cost_model_version_create_request({"currency": "swedish_krona", "terms": [term]})


@pytest.mark.parametrize(
    ("field", "value", "calculation_type"),
    [("percent_value", 1000, "percentage_of_expected_sale_price"), ("fixed_amount_minor", -1, "fixed_amount")],
    ids=["percent-over-max", "fixed-amount-negative"],
)
def test_term_request_rejects_each_excluded_numeric_boundary(field, value, calculation_type):
    term = {
        "name": "allocation",
        "calculation_type": calculation_type,
        "percent_value": 10 if calculation_type == "percentage_of_expected_sale_price" else None,
        "fixed_amount_minor": 1 if calculation_type == "fixed_amount" else None,
    }
    term[field] = value

    with pytest.raises(ValidationError, match=field):
        parse_cost_model_version_create_request({"currency": "swedish_krona", "terms": [term]})
