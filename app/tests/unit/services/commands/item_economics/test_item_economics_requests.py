from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from beyo_manager.errors.validation import ConflictError
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


def test_integrity_translation_preserves_registered_and_unknown_paths():
    known = IntegrityError(None, None, Exception("duplicate key uix_cost_model_terms_name_active"))
    with pytest.raises(ConflictError, match="^ITEM_COST_TERM_NAME_TAKEN:"):
        translate_integrity_error(known)

    unknown = IntegrityError(None, None, Exception("database connection failed"))
    with pytest.raises(IntegrityError) as raised:
        translate_integrity_error(unknown)
    assert raised.value is unknown
