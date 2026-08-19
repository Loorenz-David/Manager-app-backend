from beyo_manager.services.queries.items.lookup import purchase_api
from beyo_manager.services.queries.items.lookup_item_by_article_number import _serialize_result


class _FakeResponse:
    status_code = 200

    def json(self):
        return {
            "success": True,
            "data": {
                "article_number": "ART-1",
                "quantity": 2,
                "purchase_price": 1250.5,
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


async def test_purchase_api_lookup_preserves_purchase_price_in_serialized_result(monkeypatch):
    monkeypatch.setattr(purchase_api.settings, "beyo_vintage_api_key", "test-key")
    monkeypatch.setattr(purchase_api.httpx, "AsyncClient", _FakeAsyncClient)

    result = await purchase_api.PurchaseApiLookupHandler().lookup("ART-1", None, None, "ws_1")

    assert result is not None
    assert _serialize_result(result)["purchase_price"] == 1250.5
