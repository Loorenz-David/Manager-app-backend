import pytest

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.upholstery_providers.selfmade import (
    SelfmadeExternalUpholsteryProvider,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_selfmade_provider_returns_empty_for_empty_query() -> None:
    provider = SelfmadeExternalUpholsteryProvider()

    assert await provider.search(q="  ", limit=7) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_selfmade_provider_filters_dedupes_and_stops_when_limit_reached(monkeypatch) -> None:
    calls: list[int] = []

    async def _fake_fetch(q: str, page: int = 1) -> str:
        calls.append(page)
        return f"<html page='{page}'></html>"

    def _fake_parse(html: str) -> list[dict]:
        return [
            {
                "detail_url": "https://www.selfmade.com/sv-se/a-111/",
                "name": "A",
                "image_url": "/a.webp",
                "raw_price": "10 kr/m",
            },
            {
                "detail_url": "https://www.selfmade.com/sv-se/a-copy-111/",
                "name": "A copy",
                "image_url": "/a.webp",
                "raw_price": "10 kr/m",
            },
            {
                "detail_url": "https://www.selfmade.com/sv-se/thread-222/",
                "name": "Thread",
                "image_url": "/t.webp",
                "raw_price": "49 kr",
            },
        ]

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.selfmade.fetch_selfmade_search_html",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.selfmade.parse_selfmade_listing_candidates",
        _fake_parse,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.selfmade.has_next_selfmade_page",
        lambda html: True,
    )

    provider = SelfmadeExternalUpholsteryProvider()

    result = await provider.search(q="denim", limit=1)

    assert calls == [1]
    assert len(result) == 1
    assert result[0]["origin"] == "selfmade"
    assert result[0]["code"] == "111"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_selfmade_provider_fetches_page_two_only_when_needed(monkeypatch) -> None:
    calls: list[int] = []

    async def _fake_fetch(q: str, page: int = 1) -> str:
        calls.append(page)
        return f"<html page='{page}'></html>"

    def _fake_parse(html: str) -> list[dict]:
        if "page='1'" in html:
            return [
                {
                    "detail_url": "https://www.selfmade.com/sv-se/a-111/",
                    "name": "A",
                    "image_url": "/a.webp",
                    "raw_price": "10 kr/m",
                }
            ]
        return [
            {
                "detail_url": "https://www.selfmade.com/sv-se/b-222/",
                "name": "B",
                "image_url": "/b.webp",
                "raw_price": "20 kr/m",
            }
        ]

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.selfmade.fetch_selfmade_search_html",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.selfmade.parse_selfmade_listing_candidates",
        _fake_parse,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.selfmade.has_next_selfmade_page",
        lambda html: "page='1'" in html,
    )

    provider = SelfmadeExternalUpholsteryProvider()

    result = await provider.search(q="denim", limit=2)

    assert calls == [1, 2]
    assert [item["code"] for item in result] == ["111", "222"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_selfmade_provider_returns_empty_on_fetch_failure(monkeypatch) -> None:
    async def _fake_fetch(q: str, page: int = 1) -> str:
        raise ExternalServiceError("boom")

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.selfmade.fetch_selfmade_search_html",
        _fake_fetch,
    )

    provider = SelfmadeExternalUpholsteryProvider()

    assert await provider.search(q="denim", limit=7) == []
