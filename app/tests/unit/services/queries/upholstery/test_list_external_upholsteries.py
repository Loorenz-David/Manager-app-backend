from types import SimpleNamespace

import pytest

from beyo_manager.domain.upholstery.enums import UpholsteryExternalProviderEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.list_external_upholsteries import (
    list_external_upholsteries,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_external_upholsteries_uses_all_providers_when_none_requested(monkeypatch) -> None:
    captured = {}

    def _fake_list_providers():
        return [UpholsteryExternalProviderEnum.NEVOTEX]

    def _fake_get_provider(provider):
        captured["provider"] = provider

        class _Provider:
            async def search(self, q: str, limit: int):
                captured["q"] = q
                captured["limit"] = limit
                return [{"name": "A", "origin": provider.value, "external_url": "https://example.com/a"}]

        return _Provider()

    monkeypatch.setattr(
        "beyo_manager.services.queries.upholstery.list_external_upholsteries.list_external_upholstery_providers",
        _fake_list_providers,
    )
    monkeypatch.setattr(
        "beyo_manager.services.queries.upholstery.list_external_upholsteries.get_external_upholstery_provider",
        _fake_get_provider,
    )

    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        session=SimpleNamespace(),
        query_params={"q": "blue", "limit": 4},
    )

    result = await list_external_upholsteries(ctx)

    assert captured == {
        "provider": UpholsteryExternalProviderEnum.NEVOTEX,
        "q": "blue",
        "limit": 4,
    }
    assert result["providers"] == ["nevotex"]
    assert result["upholsteries"] == [
        {
            "name": "A",
            "origin": "nevotex",
            "external_url": "https://example.com/a",
            "supplier_name": "nevotex",
            "page_link": "https://example.com/a",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_external_upholsteries_uses_requested_provider_list(monkeypatch) -> None:
    seen = []

    def _fake_get_provider(provider):
        class _Provider:
            async def search(self, q: str, limit: int):
                seen.append((provider, q, limit))
                return [{"origin": provider.value, "external_url": "https://example.com/provider"}]

        return _Provider()

    monkeypatch.setattr(
        "beyo_manager.services.queries.upholstery.list_external_upholsteries.get_external_upholstery_provider",
        _fake_get_provider,
    )

    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        session=SimpleNamespace(),
        query_params={
            "q": "green",
            "limit": 2,
            "providers": "nevotex",
        },
    )

    result = await list_external_upholsteries(ctx)

    assert seen == [(UpholsteryExternalProviderEnum.NEVOTEX, "green", 2)]
    assert result["providers"] == ["nevotex"]
    assert result["upholsteries"] == [
        {
            "origin": "nevotex",
            "external_url": "https://example.com/provider",
            "supplier_name": "nevotex",
            "page_link": "https://example.com/provider",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_external_upholsteries_parses_csv_provider_list(monkeypatch) -> None:
    seen = []

    def _fake_get_provider(provider):
        class _Provider:
            async def search(self, q: str, limit: int):
                seen.append((provider, q, limit))
                return [{"origin": provider.value, "external_url": None}]

        return _Provider()

    monkeypatch.setattr(
        "beyo_manager.services.queries.upholstery.list_external_upholsteries.get_external_upholstery_provider",
        _fake_get_provider,
    )

    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        session=SimpleNamespace(),
        query_params={
            "q": "green",
            "limit": 2,
            "providers": "nevotex, nevotex",
        },
    )

    result = await list_external_upholsteries(ctx)

    assert seen == [(UpholsteryExternalProviderEnum.NEVOTEX, "green", 2)]
    assert result["providers"] == ["nevotex"]
    assert result["upholsteries"] == [
        {
            "origin": "nevotex",
            "external_url": None,
            "supplier_name": "nevotex",
            "page_link": None,
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_external_upholsteries_rejects_unknown_provider_name() -> None:
    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        session=SimpleNamespace(),
        query_params={"q": "blue", "providers": ["unknown-provider"]},
    )

    with pytest.raises(ValidationError, match="Invalid external upholstery provider"):
        await list_external_upholsteries(ctx)
