from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.services.commands.item_economics._common import translate_integrity_error
from beyo_manager.services.commands.item_economics.requests import (
    parse_cost_model_version_create_request,
    parse_production_cost_basis_version_create_request,
)


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
        ("uix_production_cost_group_sections_active", "ITEM_COST_SECTION_ALREADY_GROUPED"),
        ("uix_production_cost_basis_versions_open", "ITEM_COST_CONCURRENT_BASIS_VERSION"),
        ("uix_cost_model_versions_open", "ITEM_COST_CONCURRENT_MODEL_VERSION"),
        ("uix_cost_model_terms_purchase_cost", "ITEM_COST_PURCHASE_TERM_DUPLICATE"),
        ("uix_cost_model_terms_name_active", "ITEM_COST_TERM_NAME_TAKEN"),
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fixed_monthly_cost_minor", -1),
        ("monthly_paid_hours", -5),
        ("monthly_paid_hours", 0),
        ("planning_utilization_percent", 0),
        ("planning_utilization_percent", 150),
    ],
    ids=["fixed-negative", "hours-negative", "hours-zero", "util-zero", "util-over-100"],
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
