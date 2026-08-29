"""The purchase app's `attributes` payload becomes a canonical properties snapshot.

The purchase API sends its attribute list JSON-encoded inside a string, as
`[{"key": ..., "label": ..., "value": ...}]`. What the app stores and exposes is
an object keyed by attribute key — the same shape `apply_properties_snapshot`
writes and the creation endpoints accept — so a lookup result can be fed back in
without reshaping. `label` is display text owned by the purchase app and is
deliberately dropped: inside the blob it would make a rename upstream change the
item's signature and silently re-group its typical samples.
"""

import pytest

from beyo_manager.domain.items.properties_signature import compute_properties_signature
from beyo_manager.services.queries.items.lookup import purchase_api
from beyo_manager.services.queries.items.lookup.purchase_api import (
    has_attributes_payload,
    parse_purchase_api_attributes,
)
from beyo_manager.services.queries.items.lookup_item_by_article_number import _serialize_result

ENCODED_ATTRIBUTES = (
    '[{"key":"upholstery","label":"Upholstery","value":"Down"},'
    '{"key":"wood_type","label":"Type of Wood","value":"Teak"}]'
)


class _FakeResponse:
    status_code = 200
    attributes = ENCODED_ATTRIBUTES

    def json(self):
        return {
            "success": True,
            "data": {
                "article_number": "ART-1",
                "quantity": 1,
                "purchase_price": 100,
                "currency": "SEK",
                "photo_urls": [],
                "attributes": self.attributes,
            },
        }

    def raise_for_status(self):
        return None


class _FakeAsyncClient:
    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        return _FakeResponse()


def test_the_encoded_attribute_list_becomes_an_object_keyed_by_attribute_key():
    assert parse_purchase_api_attributes(ENCODED_ATTRIBUTES) == {
        "upholstery": "Down",
        "wood_type": "Teak",
    }


def test_an_already_decoded_list_is_accepted_too():
    decoded = [{"key": "wood_type", "label": "Type of Wood", "value": "Teak"}]
    assert parse_purchase_api_attributes(decoded) == {"wood_type": "Teak"}


def test_labels_stay_out_of_the_blob_so_a_rename_cannot_change_the_signature():
    renamed = ENCODED_ATTRIBUTES.replace('"Type of Wood"', '"Wood Species"')

    original = parse_purchase_api_attributes(ENCODED_ATTRIBUTES)
    after_rename = parse_purchase_api_attributes(renamed)

    assert "Type of Wood" not in str(original)
    assert compute_properties_signature(original) == compute_properties_signature(after_rename)


def test_attribute_order_does_not_change_the_signature():
    reversed_order = (
        '[{"key":"wood_type","label":"Type of Wood","value":"Teak"},'
        '{"key":"upholstery","label":"Upholstery","value":"Down"}]'
    )

    assert compute_properties_signature(
        parse_purchase_api_attributes(ENCODED_ATTRIBUTES)
    ) == compute_properties_signature(parse_purchase_api_attributes(reversed_order))


def test_a_changed_value_does_change_the_signature():
    changed = ENCODED_ATTRIBUTES.replace('"Teak"', '"Oak"')

    assert compute_properties_signature(
        parse_purchase_api_attributes(ENCODED_ATTRIBUTES)
    ) != compute_properties_signature(parse_purchase_api_attributes(changed))


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "[]",
        [],
        "not json at all",
        '{"key": "wood_type"}',  # an object, not a list
        '["wood_type"]',  # entries that are not objects
        '[{"label": "No key", "value": "x"}]',
        '[{"key": "   ", "value": "x"}]',
        '[{"key": "wood_type"}]',  # no value
        '[{"key": "wood_type", "value": null}]',
        '[{"key": "wood_type", "value": "   "}]',
        42,
    ],
)
def test_anything_unusable_degrades_to_an_empty_snapshot_rather_than_raising(raw):
    """An empty snapshot is inert on the write path, so it can never clear a profile."""
    assert parse_purchase_api_attributes(raw) == {}


def test_a_duplicate_key_keeps_the_first_value():
    raw = (
        '[{"key":"wood_type","value":"Teak"},'
        '{"key":"wood_type","value":"Oak"}]'
    )
    assert parse_purchase_api_attributes(raw) == {"wood_type": "Teak"}


def test_a_usable_entry_survives_an_unusable_sibling():
    raw = '[{"key":"","value":"dropped"},{"key":"wood_type","value":"Teak"}]'
    assert parse_purchase_api_attributes(raw) == {"wood_type": "Teak"}


def test_non_string_values_pass_through_verbatim():
    raw = '[{"key":"drawers","value":3},{"key":"restored","value":false}]'
    assert parse_purchase_api_attributes(raw) == {"drawers": 3, "restored": False}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (ENCODED_ATTRIBUTES, True),
        ("garbage", True),
        ([{"key": "a", "value": "b"}], True),
        (None, False),
        ("", False),
        ("   ", False),
        ("[]", False),
        ([], False),
    ],
)
def test_has_attributes_payload_separates_absent_from_unreadable(raw, expected):
    """The parser collapses both to {}; only "sent but unreadable" deserves attention."""
    assert has_attributes_payload(raw) is expected


async def test_the_lookup_returns_properties_as_an_object(monkeypatch):
    monkeypatch.setattr(purchase_api.settings, "beyo_vintage_api_key", "test-key")
    monkeypatch.setattr(purchase_api.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(_FakeResponse, "attributes", ENCODED_ATTRIBUTES)

    result = await purchase_api.PurchaseApiLookupHandler().lookup("ART-1", None, None, "ws_1")

    assert result is not None
    assert _serialize_result(result)["properties"] == {
        "upholstery": "Down",
        "wood_type": "Teak",
    }


async def test_an_item_with_no_attributes_reports_properties_as_none(monkeypatch):
    """None and {} are identical to the write path, so neither can wipe a profile."""
    monkeypatch.setattr(purchase_api.settings, "beyo_vintage_api_key", "test-key")
    monkeypatch.setattr(purchase_api.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(_FakeResponse, "attributes", None)

    result = await purchase_api.PurchaseApiLookupHandler().lookup("ART-1", None, None, "ws_1")

    assert result is not None
    assert _serialize_result(result)["properties"] is None
