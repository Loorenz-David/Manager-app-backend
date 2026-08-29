"""Unit tests for the pure decision logic of the purchase API backfill.

The script backfills two independent fields from one lookup — purchase_cost and
properties — so decide() returns one plan per field and every test here asserts
on the plan for the field it is about.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.items.properties_signature import compute_properties_signature
from scripts.purchase_api.backfill_from_purchase_api import (
    ACTION_SKIP,
    ACTION_UPDATE,
    FIELD_PROPERTIES,
    FIELD_PURCHASE_COST,
    ItemSnapshot,
    Lookup,
    decide,
    established_properties_signature,
)

ENCODED_ATTRIBUTES = (
    '[{"key":"upholstery","label":"Upholstery","value":"Down"},'
    '{"key":"wood_type","label":"Type of Wood","value":"Teak"}]'
)
PARSED_ATTRIBUTES = {"upholstery": "Down", "wood_type": "Teak"}


def _valuation(expected=None, purchase=50000, currency=ItemCurrencyEnum.SWEDISH_KRONA):
    return SimpleNamespace(
        expected_sale_price_minor=expected,
        purchase_cost_minor=purchase,
        currency=currency,
    )


def _item(
    *,
    quantity=1,
    valuation=None,
    properties=None,
    established_signature=None,
):
    return ItemSnapshot(
        client_id="itm_1",
        article_number="4711",
        quantity=quantity,
        valuation=valuation,
        properties=properties,
        established_properties_signature=established_signature,
    )


def _lookup(**data):
    payload = {
        "article_number": "4711",
        "purchase_price": 100,
        "currency": "SEK",
        "attributes": ENCODED_ATTRIBUTES,
    }
    payload.update(data)
    return Lookup(status="ok", data=payload)


def _plan(plans, field_name):
    matches = [plan for plan in plans if plan.field_name == field_name]
    assert len(matches) == 1, f"expected exactly one {field_name} plan, got {len(matches)}"
    return matches[0]


def _decide(item, lookup):
    return decide(item=item, lookup=lookup)


# --- every field gets a plan, always -----------------------------------------


def test_every_call_returns_one_plan_per_backfilled_field():
    plans = _decide(_item(), _lookup())
    assert sorted(plan.field_name for plan in plans) == [FIELD_PROPERTIES, FIELD_PURCHASE_COST]


@pytest.mark.parametrize(
    ("lookup", "expected_reason"),
    [
        (Lookup(status="not_found"), "not_found"),
        (Lookup(status="invalid"), "invalid_article_number"),
        (Lookup(status="api_reported_failure"), "api_reported_failure"),
    ],
)
def test_a_failed_lookup_blocks_both_fields_with_the_same_reason(lookup, expected_reason):
    plans = _decide(_item(), lookup)

    assert [plan.action for plan in plans] == [ACTION_SKIP, ACTION_SKIP]
    assert {plan.reason for plan in plans} == {expected_reason}


def test_an_article_number_the_api_swapped_blocks_both_fields():
    plans = _decide(_item(), _lookup(article_number="9999"))

    assert {(plan.action, plan.reason) for plan in plans} == {
        (ACTION_SKIP, "article_number_mismatch")
    }


# --- properties ---------------------------------------------------------------


def test_an_item_with_no_profile_gets_its_first_snapshot():
    plan = _plan(_decide(_item(), _lookup()), FIELD_PROPERTIES)

    assert (plan.action, plan.reason) == (ACTION_UPDATE, "first_snapshot")
    assert plan.payload == PARSED_ATTRIBUTES
    assert plan.expected_current is None


def test_a_different_profile_is_planned_as_a_change():
    stored = {"wood_type": "Oak"}
    plan = _plan(
        _decide(
            _item(properties=stored, established_signature=compute_properties_signature(stored)),
            _lookup(),
        ),
        FIELD_PROPERTIES,
    )

    assert (plan.action, plan.reason) == (ACTION_UPDATE, "profile_changed")
    assert plan.payload == PARSED_ATTRIBUTES
    assert plan.expected_current == compute_properties_signature(stored)


def test_the_same_profile_writes_nothing_so_snapshot_at_keeps_its_meaning():
    plan = _plan(
        _decide(
            _item(
                properties=PARSED_ATTRIBUTES,
                established_signature=compute_properties_signature(PARSED_ATTRIBUTES),
            ),
            _lookup(),
        ),
        FIELD_PROPERTIES,
    )

    assert (plan.action, plan.reason) == (ACTION_SKIP, "unchanged")


def test_reordered_attributes_are_the_same_profile():
    reversed_order = (
        '[{"key":"wood_type","label":"Type of Wood","value":"Teak"},'
        '{"key":"upholstery","label":"Upholstery","value":"Down"}]'
    )
    plan = _plan(
        _decide(
            _item(
                properties=PARSED_ATTRIBUTES,
                established_signature=compute_properties_signature(PARSED_ATTRIBUTES),
            ),
            _lookup(attributes=reversed_order),
        ),
        FIELD_PROPERTIES,
    )

    assert (plan.action, plan.reason) == (ACTION_SKIP, "unchanged")


@pytest.mark.parametrize("attributes", [None, "", "[]", []])
def test_an_item_the_purchase_app_has_no_attributes_for_is_skipped_quietly(attributes):
    plan = _plan(_decide(_item(), _lookup(attributes=attributes)), FIELD_PROPERTIES)

    assert (plan.action, plan.reason) == (ACTION_SKIP, "no_attributes")


@pytest.mark.parametrize("attributes", ["not json", '{"key": "x"}', '[{"label": "no key"}]'])
def test_attributes_that_arrived_but_could_not_be_read_are_flagged_separately(attributes):
    """Distinct from no_attributes: something was sent and the run should say so."""
    plan = _plan(_decide(_item(), _lookup(attributes=attributes)), FIELD_PROPERTIES)

    assert (plan.action, plan.reason) == (ACTION_SKIP, "unparsable_attributes")


def test_a_signature_without_a_snapshot_time_is_not_an_established_profile():
    """apply_properties_snapshot writes straight through it, so planning must too."""
    item = SimpleNamespace(
        properties_signature=compute_properties_signature(PARSED_ATTRIBUTES),
        properties_snapshot_at=None,
    )
    assert established_properties_signature(item) is None

    plan = _plan(_decide(_item(established_signature=None), _lookup()), FIELD_PROPERTIES)
    assert plan.action == ACTION_UPDATE


def test_a_signature_with_a_snapshot_time_is_established():
    item = SimpleNamespace(
        properties_signature="abc",
        properties_snapshot_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    assert established_properties_signature(item) == "abc"


# --- purchase cost ------------------------------------------------------------


def test_purchase_price_is_converted_and_multiplied_by_quantity():
    plan = _plan(_decide(_item(quantity=3), _lookup(purchase_price=100)), FIELD_PURCHASE_COST)

    assert plan.action == ACTION_UPDATE
    assert plan.payload["purchase_cost_minor"] == 30000


def test_an_unchanged_purchase_cost_is_skipped():
    plan = _plan(
        _decide(_item(valuation=_valuation(purchase=10000)), _lookup(purchase_price=100)),
        FIELD_PURCHASE_COST,
    )

    assert (plan.action, plan.reason) == (ACTION_SKIP, "unchanged")


def test_an_unsupported_currency_skips_only_the_price():
    plans = _decide(_item(), _lookup(currency="USD"))

    assert _plan(plans, FIELD_PURCHASE_COST).reason == "unsupported_currency"
    assert _plan(plans, FIELD_PROPERTIES).action == ACTION_UPDATE


def test_a_foreign_currency_valuation_is_not_overwritten():
    plan = _plan(
        _decide(_item(valuation=_valuation(currency=ItemCurrencyEnum.EURO)), _lookup()),
        FIELD_PURCHASE_COST,
    )

    assert (plan.action, plan.reason) == (ACTION_SKIP, "currency_conflict")


def test_an_existing_expected_sale_price_survives_the_backfill():
    plan = _plan(
        _decide(_item(valuation=_valuation(expected=120000, purchase=1)), _lookup()),
        FIELD_PURCHASE_COST,
    )

    assert plan.payload["expected_sale_price_minor"] == 120000


# --- the two fields are independent -------------------------------------------


def test_a_price_that_cannot_be_written_does_not_cost_the_properties():
    plans = _decide(_item(quantity=0), _lookup())

    assert _plan(plans, FIELD_PURCHASE_COST).reason == "non_positive_quantity"
    assert _plan(plans, FIELD_PROPERTIES).action == ACTION_UPDATE


def test_missing_attributes_do_not_cost_the_price():
    plans = _decide(_item(), _lookup(attributes=None))

    assert _plan(plans, FIELD_PROPERTIES).reason == "no_attributes"
    assert _plan(plans, FIELD_PURCHASE_COST).action == ACTION_UPDATE
