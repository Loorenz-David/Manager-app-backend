import pytest

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.upholstery_providers.ohlssons_tyger import (
    OhlssonsTygerExternalUpholsteryProvider,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_returns_normalized_candidates(monkeypatch) -> None:
    async def _fake_search_html(q: str, limit: int) -> str:
        assert q == "viscose"
        assert limit == 2
        return "<html />"

    async def _fake_detail_html(url: str) -> str:
        return f"<html>{url}</html>"

    def _fake_parse_listing(html: str, base_url: str, limit: int | None = None) -> list[dict]:
        assert limit == 2
        return [
            {"detail_url": "https://www.ohlssonstyger.se/sv/artikel/a", "name": "A", "image_url": "/a.jpg"},
            {"detail_url": "https://www.ohlssonstyger.se/sv/artikel/b", "name": "B", "image_url": "/b.jpg"},
        ]

    def _fake_parse_detail(
        html: str,
        detail_url: str,
        base_url: str,
        fallback_name: str = "",
        fallback_image: str = "",
    ) -> dict:
        return {
            "name": fallback_name or detail_url.rsplit("/", 1)[-1],
            "code": detail_url.rsplit("/", 1)[-1].upper(),
            "image": fallback_image or "/fallback.jpg",
            "detail_url": detail_url,
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.ohlssons_tyger.fetch_ohlssons_tyger_search_html",
        _fake_search_html,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.ohlssons_tyger.fetch_ohlssons_tyger_detail_html",
        _fake_detail_html,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.ohlssons_tyger.parse_ohlssons_tyger_listing_candidates",
        _fake_parse_listing,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.ohlssons_tyger.parse_ohlssons_tyger_detail",
        _fake_parse_detail,
    )

    provider = OhlssonsTygerExternalUpholsteryProvider()

    result = await provider.search(q="viscose", limit=2)

    assert [item["origin"] for item in result] == ["ohlssons_tyger", "ohlssons_tyger"]
    assert [item["code"] for item in result] == ["A", "B"]
    assert [item["external_url"] for item in result] == [
        "https://www.ohlssonstyger.se/sv/artikel/a",
        "https://www.ohlssonstyger.se/sv/artikel/b",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_returns_empty_list_when_search_fetch_fails(monkeypatch) -> None:
    async def _fake_search_html(q: str, limit: int) -> str:
        raise ExternalServiceError("boom")

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.ohlssons_tyger.fetch_ohlssons_tyger_search_html",
        _fake_search_html,
    )

    provider = OhlssonsTygerExternalUpholsteryProvider()

    result = await provider.search(q="viscose", limit=2)

    assert result == []
