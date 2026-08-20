import pytest

from beyo_manager.services.queries.items.lookup import purchase_api
from beyo_manager.services.queries.items.lookup_item_by_article_number import (
    _serialize_result,
)


class _FakeResponse:
    status_code = 200
    currency = "SEK"
    purchase_price = 1250.5

    def json(self):
        return {
            "success": True,
            "data": {
                "article_number": "ART-1",
                "quantity": 2,
                "purchase_price": self.purchase_price,
                "currency": self.currency,
                "photo_urls": [],
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


@pytest.mark.parametrize(
    ("currency", "purchase_price", "expected_sek_minor"),
    [
        ("EUR", 1250.5, 1375550),
        ("DKK", 1250.5, 187575),
        ("SEK", 1250.5, 125050),
    ],
)
async def test_purchase_api_lookup_normalizes_purchase_price_to_sek_minor(
    monkeypatch,
    currency,
    purchase_price,
    expected_sek_minor,
):
    monkeypatch.setattr(purchase_api.settings, "beyo_vintage_api_key", "test-key")
    monkeypatch.setattr(purchase_api.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(_FakeResponse, "currency", currency)
    monkeypatch.setattr(_FakeResponse, "purchase_price", purchase_price)

    result = await purchase_api.PurchaseApiLookupHandler().lookup(
        "ART-1", None, None, "ws_1"
    )

    assert result is not None
    assert _serialize_result(result)["purchase_price_minor"] == expected_sek_minor


async def test_purchase_api_lookup_rejects_purchase_price_without_supported_currency(
    monkeypatch,
):
    monkeypatch.setattr(purchase_api.settings, "beyo_vintage_api_key", "test-key")
    monkeypatch.setattr(purchase_api.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(_FakeResponse, "currency", "USD")

    with pytest.raises(ValueError, match="unsupported currency 'USD'"):
        await purchase_api.PurchaseApiLookupHandler().lookup(
            "ART-1", None, None, "ws_1"
        )
