"""Unit tests for the pure decision logic of the Shopify backfill field registry."""

from types import SimpleNamespace

import pytest

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from scripts.shopify import backfill_from_shopify as backfill
from scripts.shopify.fields import (
    ACTION_SKIP,
    ACTION_UPDATE,
    ExpectedSoldPriceBackfiller,
    ShopifySnapshot,
    _parse_price_minor,
)

BACKFILLER = ExpectedSoldPriceBackfiller()


def _valuation(expected=120000, purchase=50000, currency=ItemCurrencyEnum.SWEDISH_KRONA):
    return SimpleNamespace(
        expected_sale_price_minor=expected,
        purchase_cost_minor=purchase,
        currency=currency,
    )


def _decide(current_valuation, matches, shop_currency_code="SEK"):
    return BACKFILLER.decide(
        item_client_id="itm_1",
        article_number="4711",
        current_valuation=current_valuation,
        snapshot=ShopifySnapshot(variant_matches=matches, shop_currency_code=shop_currency_code),
    )


def test_no_match_skips_not_found():
    plan = _decide(_valuation(), [])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "not_found")


def test_multiple_exact_matches_skip_ambiguous():
    plan = _decide(_valuation(), [{"price": "100.00"}, {"price": "200.00"}])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "ambiguous")


@pytest.mark.parametrize("price", [None, "", "abc"])
def test_missing_or_malformed_price_skips_no_price(price):
    plan = _decide(_valuation(), [{"price": price}])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "no_price")


def test_unmapped_shop_currency_skips_unsupported():
    plan = _decide(_valuation(), [{"price": "100.00"}], shop_currency_code="USD")
    assert (plan.action, plan.reason) == (ACTION_SKIP, "unsupported_currency")


def test_currency_conflict_with_current_valuation_skips():
    plan = _decide(_valuation(currency=ItemCurrencyEnum.EURO), [{"price": "100.00"}], shop_currency_code="SEK")
    assert (plan.action, plan.reason) == (ACTION_SKIP, "currency_conflict")


def test_identical_triple_skips_unchanged():
    plan = _decide(_valuation(expected=120000), [{"price": "1200.00"}])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "unchanged")


def test_changed_price_updates_and_inherits_purchase_cost_and_currency():
    plan = _decide(_valuation(expected=120000, purchase=50000), [{"price": "1350.00"}])
    assert plan.action == ACTION_UPDATE
    assert plan.reason == "price_changed"
    assert plan.payload == {
        "item_client_id": "itm_1",
        "expected_sale_price_minor": 135000,
        "purchase_cost_minor": 50000,
        "currency": ItemCurrencyEnum.SWEDISH_KRONA.value,
    }
    assert plan.expected_current == (120000, 50000, ItemCurrencyEnum.SWEDISH_KRONA)


def test_no_current_valuation_writes_first_valuation_in_shop_currency():
    plan = _decide(None, [{"price": "999.90"}])
    assert plan.action == ACTION_UPDATE
    assert plan.reason == "first_valuation"
    assert plan.payload == {
        "item_client_id": "itm_1",
        "expected_sale_price_minor": 99990,
        "purchase_cost_minor": None,
        "currency": ItemCurrencyEnum.SWEDISH_KRONA.value,
    }
    assert plan.expected_current is None


def test_price_equal_but_purchase_cost_null_current_still_updates():
    # Same price, but the current row has no purchase cost and the new one inherits it — triple equal → unchanged.
    plan = _decide(_valuation(expected=100000, purchase=None), [{"price": "1000.00"}])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "unchanged")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234.50", 123450),
        ("0.005", 0),        # HALF_EVEN to 0.00
        ("0.015", 2),        # HALF_EVEN to 0.02
        ("100", 10000),
        ("-1", None),
        (True, None),
    ],
)
def test_parse_price_minor(raw, expected):
    assert _parse_price_minor(raw) == expected


def _item(client_id: str, article_number):
    return SimpleNamespace(client_id=client_id, article_number=article_number)


def test_chunked_splits_into_batches_without_losing_items():
    items = [_item(f"itm_{n}", str(n)) for n in range(250)]

    batches = backfill.chunked(items, backfill.BARCODE_BATCH_SIZE)

    assert [len(batch) for batch in batches] == [100, 100, 50]
    assert [item.client_id for batch in batches for item in batch] == [item.client_id for item in items]


def test_chunked_of_empty_list_is_no_batches():
    assert backfill.chunked([], backfill.BARCODE_BATCH_SIZE) == []


@pytest.mark.parametrize("blank_value", [None, "", "   "])
def test_partition_separates_unusable_article_numbers(blank_value):
    usable, blank = backfill.partition_by_article_number([_item("itm_1", "A-1"), _item("itm_2", blank_value)])

    assert [item.client_id for item in usable] == ["itm_1"]
    assert [item.client_id for item in blank] == ["itm_2"]


def test_duplicate_listings_that_agree_on_price_resolve_instead_of_blocking():
    plan = _decide(_valuation(expected=120000, purchase=50000), [{"price": "26500.00"}, {"price": "26500.00"}])

    assert plan.action == ACTION_UPDATE
    assert plan.reason == "price_changed (2 listings agree)"
    assert plan.payload["expected_sale_price_minor"] == 2650000
    assert plan.payload["purchase_cost_minor"] == 50000


def test_duplicate_listings_that_disagree_on_price_stay_ambiguous():
    plan = _decide(_valuation(), [{"price": "26500.00"}, {"price": "30000.00"}])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "ambiguous")


def test_duplicate_where_one_listing_has_no_price_stays_ambiguous():
    # A missing price is not agreement — there is still no basis to pick one.
    plan = _decide(_valuation(), [{"price": "26500.00"}, {"price": None}])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "ambiguous")


def test_duplicates_all_missing_a_price_report_no_price_not_ambiguous():
    plan = _decide(_valuation(), [{"price": None}, {"price": None}])
    assert (plan.action, plan.reason) == (ACTION_SKIP, "no_price")


def test_agreeing_duplicates_still_respect_unchanged_and_currency_rules():
    unchanged = _decide(_valuation(expected=2650000, purchase=50000), [{"price": "26500.00"}, {"price": "26500.00"}])
    assert (unchanged.action, unchanged.reason) == (ACTION_SKIP, "unchanged")

    conflicting = _decide(
        _valuation(currency=ItemCurrencyEnum.EURO), [{"price": "26500.00"}, {"price": "26500.00"}]
    )
    assert (conflicting.action, conflicting.reason) == (ACTION_SKIP, "currency_conflict")
