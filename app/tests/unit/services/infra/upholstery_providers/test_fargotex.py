import asyncio

import pytest

from beyo_manager.services.infra.upholstery_providers.fargotex import (
    FargotexExternalUpholsteryProvider,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_filters_matches_and_stops_when_limit_reached(monkeypatch) -> None:
    calls: list[int] = []

    async def _fake_fetch(page: int = 1) -> str:
        calls.append(page)
        return f"<html page='{page}'></html>"

    def _fake_parse(html: str) -> list[dict]:
        if "page='1'" in html:
            return [
                {
                    "name": "Noma",
                    "code": "55379",
                    "image": "https://fargotex.pl/wp-content/uploads/noma.webp",
                    "external_url": "https://fargotex.pl/produkt/noma/",
                },
                {
                    "name": "Alia",
                    "code": "55348",
                    "image": "https://fargotex.pl/wp-content/uploads/alia.webp",
                    "external_url": "https://fargotex.pl/produkt/alia/",
                },
            ]
        return [
            {
                "name": "Noma Plus",
                "code": "99999",
                "image": "https://fargotex.pl/wp-content/uploads/noma-plus.webp",
                "external_url": "https://fargotex.pl/produkt/noma-plus/",
            }
        ]

    def _fake_has_next(html: str) -> bool:
        return "page='1'" in html

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        _fake_parse,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        _fake_has_next,
    )

    provider = FargotexExternalUpholsteryProvider()

    result = await provider.search(q="noma", limit=1)

    assert calls == [1, 2, 3]
    assert len(result) == 1
    assert result[0]["name"] == "Noma"
    assert result[0]["origin"] == "fargotex"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_stops_when_no_next_page(monkeypatch) -> None:
    calls: list[int] = []

    async def _fake_fetch(page: int = 1) -> str:
        calls.append(page)
        return "<html></html>"

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        lambda html: [],
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        lambda html: False,
    )

    provider = FargotexExternalUpholsteryProvider()

    result = await provider.search(q="noma", limit=7)

    assert calls == [1, 2, 3]
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_fetches_pages_concurrently(monkeypatch) -> None:
    started_pages: list[int] = []
    release = asyncio.Event()
    all_started = asyncio.Event()

    async def _fake_fetch(page: int = 1) -> str:
        started_pages.append(page)
        if len(started_pages) == 3:
            all_started.set()
        await release.wait()
        return f"<html page='{page}'></html>"

    def _fake_parse(html: str) -> list[dict]:
        return []

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        _fake_parse,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        lambda html: False,
    )

    provider = FargotexExternalUpholsteryProvider()
    task = asyncio.create_task(provider.search(q="noma", limit=7))

    await asyncio.wait_for(all_started.wait(), timeout=1)
    release.set()
    result = await task

    assert started_pages == [1, 2, 3]
    assert result == []
