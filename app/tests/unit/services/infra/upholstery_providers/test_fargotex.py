import asyncio

import pytest

from beyo_manager.services.infra.upholstery_providers.fargotex import (
    FargotexExternalUpholsteryProvider,
    build_fargotex_gallery_candidates,
    resolve_fargotex_gallery_sample_code,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_filters_matches_and_stops_when_limit_reached(monkeypatch) -> None:
    calls: list[int] = []
    product_calls: list[str] = []

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

    async def _fake_product_fetch(product_url: str) -> str:
        product_calls.append(product_url)
        raise RuntimeError("product page unavailable")

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_product_html",
        _fake_product_fetch,
    )

    provider = FargotexExternalUpholsteryProvider()

    result = await provider.search(q="noma", limit=1)

    assert calls == [1, 2, 3]
    assert len(result) == 1
    assert result[0]["name"] == "Noma"
    assert result[0]["origin"] == "fargotex"
    assert product_calls == ["https://fargotex.pl/produkt/noma/"]


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_discovers_parent_beyond_initial_page_wave(monkeypatch) -> None:
    calls: list[int] = []

    async def _fake_fetch_page(page: int = 1) -> str:
        calls.append(page)
        return f"page-{page}"

    def _fake_parse_listing(html: str) -> list[dict]:
        if html == "page-7":
            return [
                {
                    "name": "Neon",
                    "code": "53035",
                    "image": "/uploads/neon.webp",
                    "external_url": "/produkt/neon/",
                }
            ]
        return []

    def _fake_has_next(html: str) -> bool:
        return html != "page-7"

    async def _fake_fetch_product(product_url: str) -> str:
        raise RuntimeError("product detail not needed for pagination test")

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch_page,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        _fake_parse_listing,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        _fake_has_next,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_product_html",
        _fake_fetch_product,
    )

    result = await FargotexExternalUpholsteryProvider().search(q="neon", limit=10)

    assert calls == list(range(1, 10))
    assert len(result) == 1
    assert result[0]["name"] == "Neon"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_expands_matching_parent_into_variations(monkeypatch) -> None:
    product_calls: list[str] = []

    async def _fake_fetch_page(page: int = 1) -> str:
        return "<html page='1'></html>" if page == 1 else "<html></html>"

    def _fake_parse_listing(html: str) -> list[dict]:
        if "page='1'" not in html:
            return []
        return [
            {
                "name": "Neon",
                "code": "55379",
                "image": "/uploads/neon.webp",
                "external_url": "/produkt/neon/",
            }
        ]

    async def _fake_fetch_product(product_url: str) -> str:
        product_calls.append(product_url)
        return "neon-product"

    variations = [
        {
            "variation_id": str(66747 + index),
            "sku": "shared-sku",
            "variant_name": label,
            "image": "",
        }
        for index, label in enumerate(
            ["antracyt", "czerwony", "pomarancz", "beżowy", "szary", "zielony"]
        )
    ]

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch_page,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        _fake_parse_listing,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        lambda html: False,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_product_html",
        _fake_fetch_product,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_variations",
        lambda html: variations,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_gallery",
        lambda html: [],
    )

    result = await FargotexExternalUpholsteryProvider().search(q="NeOn", limit=7)

    assert product_calls == ["https://fargotex.pl/produkt/neon/"]
    assert len(result) == 6
    assert [item["code"] for item in result] == [str(66747 + index) for index in range(6)]
    assert [item["name"] for item in result] == [
        "Neon antracyt",
        "Neon czerwony",
        "Neon pomarancz",
        "Neon beżowy",
        "Neon szary",
        "Neon zielony",
    ]
    assert {item["sku"] for item in result} == {"shared-sku"}
    assert all(item["variation_id"] == item["code"] for item in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_final_limit_counts_expanded_variations(monkeypatch) -> None:
    parents = [
        {
            "name": "Neon",
            "code": "55379",
            "image": "/uploads/neon.webp",
            "external_url": "/produkt/neon/",
        },
        {
            "name": "Neon Plus",
            "code": "55380",
            "image": "/uploads/neon-plus.webp",
            "external_url": "/produkt/neon-plus/",
        },
    ]

    async def _fake_fetch_page(page: int = 1) -> str:
        return "category"

    def _fake_parse_listing(html: str) -> list[dict]:
        return parents

    async def _fake_fetch_product(product_url: str) -> str:
        return product_url

    def _fake_parse_variations(product_url: str) -> list[dict]:
        parent_name = "Neon Plus" if "plus" in product_url else "Neon"
        start = 70000 if parent_name == "Neon" else 71000
        count = 6 if parent_name == "Neon" else 2
        return [
            {
                "variation_id": str(start + index),
                "variant_name": f"color-{index}",
                "sku": "shared-sku",
                "image": "",
            }
            for index in range(count)
        ]

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch_page,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        _fake_parse_listing,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        lambda html: False,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_product_html",
        _fake_fetch_product,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_variations",
        _fake_parse_variations,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_gallery",
        lambda html: [],
    )

    result = await FargotexExternalUpholsteryProvider().search(q="neon", limit=7)

    assert len(result) == 7
    assert [item["parent_name"] for item in result] == ["Neon"] * 6 + ["Neon Plus"]
    assert [item["code"] for item in result] == [
        *(str(70000 + index) for index in range(6)),
        "71000",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_returns_parent_on_empty_variations(monkeypatch) -> None:
    async def _fake_fetch_page(page: int = 1) -> str:
        return "category"

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch_page,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        lambda html: [
            {
                "name": "Simple Neon",
                "code": "55379",
                "image": "/uploads/neon.webp",
                "external_url": "/produkt/neon/",
            }
        ],
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        lambda html: False,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_product_html",
        _fake_empty_product_fetch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_variations",
        lambda html: [],
    )

    result = await FargotexExternalUpholsteryProvider().search(q="neon", limit=7)

    assert len(result) == 1
    assert result[0]["name"] == "Simple Neon"
    assert "variation_id" not in result[0]


@pytest.mark.unit
def test_build_fargotex_gallery_candidates_filters_main_non_numbered_and_duplicates() -> None:
    parent = {
        "name": "Neon",
        "code": "53035",
        "external_url": "https://fargotex.pl/produkt/neon/",
    }
    gallery_images = [
        {
            "position": 1,
            "image_code": "01",
            "image_url": "https://fargotex.pl/uploads/neon.webp",
            "is_main": True,
        },
        {
            "position": 2,
            "image_code": "01",
            "image_url": "https://fargotex.pl/uploads/neon-01-w-1200.webp",
            "media_id": "10",
            "is_main": False,
        },
        {
            "position": 3,
            "image_code": "02",
            "image_url": "https://fargotex.pl/uploads/neon-02-w-1200.webp",
            "media_id": "11",
            "is_main": False,
        },
        {
            "position": 4,
            "image_code": "",
            "image_url": "https://fargotex.pl/uploads/neon-room.webp",
            "is_main": False,
        },
        {
            "position": 5,
            "image_code": "01",
            "image_url": "https://fargotex.pl/uploads/neon-01-alt.webp",
            "is_main": False,
        },
        {
            "position": 6,
            "image_code": "03",
            "image_url": "https://fargotex.pl/uploads/neon-03-w-1200.webp",
            "media_id": "10",
            "is_main": False,
        },
    ]

    result = build_fargotex_gallery_candidates(parent, gallery_images)

    assert [item["code"] for item in result] == ["53035-01", "53035-02"]
    assert [item["name"] for item in result] == ["Neon 01", "Neon 02"]
    assert [item["variant_name"] for item in result] == ["01", "02"]
    assert [item["gallery_code"] for item in result] == ["01", "02"]
    assert [item["gallery_position"] for item in result] == ["2", "3"]
    assert result[0]["image"] == "https://fargotex.pl/uploads/neon-01-w-1200.webp"


@pytest.mark.unit
def test_build_fargotex_gallery_candidates_keep_same_sample_code_separate_by_parent() -> None:
    first = build_fargotex_gallery_candidates(
        {"name": "Neon", "code": "53035"},
        [
            {
                "position": 2,
                "image_url": "https://fargotex.pl/uploads/neon-01.webp",
                "is_main": False,
            }
        ],
    )
    second = build_fargotex_gallery_candidates(
        {"name": "Noma", "code": "55379"},
        [
            {
                "position": 2,
                "image_url": "https://fargotex.pl/uploads/noma-01.webp",
                "is_main": False,
            }
        ],
    )

    assert first[0]["code"] == "53035-01"
    assert second[0]["code"] == "55379-01"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("parent", "image_url", "expected_code", "expected_reason"),
    [
        (
            {"name": "Neon", "external_url": "https://fargotex.pl/produkt/neon/"},
            "https://fargotex.pl/uploads/neon-01-w-1200.webp",
            "01",
            "parent_filename",
        ),
        (
            {"name": "Neon", "external_url": "https://fargotex.pl/produkt/neon/"},
            "https://fargotex.pl/uploads/49neon-03-w-1200.webp",
            "03",
            "parent_filename",
        ),
        (
            {"name": "Nebbia", "external_url": "https://fargotex.pl/produkt/nebbia/"},
            "https://fargotex.pl/uploads/921nebbia05-w-1200.jpg",
            "05",
            "parent_filename",
        ),
        (
            {"name": "Tulia New", "external_url": "https://fargotex.pl/produkt/tulia/"},
            "https://fargotex.pl/uploads/Tulia02_2.webp",
            "02",
            "parent_filename",
        ),
        (
            {"name": "Neon", "external_url": "https://fargotex.pl/produkt/neon/"},
            "https://fargotex.pl/uploads/neon-100x100.webp",
            None,
            "no_parent_associated_code",
        ),
        (
            {"name": "Neon", "external_url": "https://fargotex.pl/produkt/neon/"},
            "https://fargotex.pl/uploads/room-01.webp",
            None,
            "no_parent_associated_code",
        ),
        (
            {"name": "Neon New", "external_url": "https://fargotex.pl/produkt/neon/"},
            "https://fargotex.pl/uploads/new-01.webp",
            None,
            "no_parent_associated_code",
        ),
        (
            {"name": "Neon", "external_url": "https://fargotex.pl/produkt/neon/"},
            "https://fargotex.pl/uploads/neon-01-neon-02.webp",
            None,
            "ambiguous_parent_associated_codes",
        ),
    ],
)
def test_resolve_fargotex_gallery_sample_code_requires_unambiguous_parent_association(
    parent: dict,
    image_url: str,
    expected_code: str | None,
    expected_reason: str,
) -> None:
    code, reason = resolve_fargotex_gallery_sample_code(parent, {"image_url": image_url})

    assert code == expected_code
    assert reason == expected_reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_prefers_numbered_gallery_over_woocommerce_variations(
    monkeypatch,
) -> None:
    parent = {
        "name": "Neon",
        "code": "53035",
        "image": "/uploads/neon.webp",
        "external_url": "/produkt/neon/",
    }
    gallery = [
        {
            "position": 1,
            "image_code": "",
            "image_url": "https://fargotex.pl/uploads/neon.webp",
            "is_main": True,
        }
    ] + [
        {
            "position": index + 1,
            "image_code": f"{index:02d}",
            "image_url": f"https://fargotex.pl/uploads/neon-{index:02d}-w-1200.webp",
            "is_main": False,
        }
        for index in range(1, 9)
    ]
    variations = [
        {
            "variation_id": str(66747 + index),
            "variant_name": f"color-{index}",
            "sku": "shared-sku",
            "image": "https://fargotex.pl/uploads/neon.webp",
        }
        for index in range(6)
    ]

    async def _fake_fetch_page(page: int = 1) -> str:
        return "category"

    async def _fake_fetch_product(product_url: str) -> str:
        return "product"

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch_page,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        lambda html: [parent],
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        lambda html: False,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_product_html",
        _fake_fetch_product,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_gallery",
        lambda html: gallery,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_variations",
        lambda html: variations,
    )

    result = await FargotexExternalUpholsteryProvider().search(q="neon", limit=20)

    assert len(result) == 8
    assert [item["code"] for item in result] == [f"53035-{index:02d}" for index in range(1, 9)]
    assert [item["name"] for item in result] == [f"Neon {index:02d}" for index in range(1, 9)]
    assert [item["gallery_position"] for item in result] == [str(index) for index in range(2, 10)]
    assert all("variation_id" not in item for item in result)
    assert all(item["image_url"].endswith(f"{index:02d}-w-1200.webp") for index, item in enumerate(result, 1))

    limited = await FargotexExternalUpholsteryProvider().search(q="neon", limit=5)
    assert [item["code"] for item in limited] == [f"53035-{index:02d}" for index in range(1, 6)]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fargotex_provider_uses_woocommerce_variations_when_gallery_parse_fails(
    monkeypatch,
) -> None:
    parent = {
        "name": "Noma",
        "code": "55379",
        "image": "/uploads/noma.webp",
        "external_url": "/produkt/noma/",
    }

    async def _fake_fetch_page(page: int = 1) -> str:
        return "category"

    async def _fake_fetch_product(product_url: str) -> str:
        return "product"

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_category_html",
        _fake_fetch_page,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_listing_candidates",
        lambda html: [parent],
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.has_next_fargotex_page",
        lambda html: False,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.fetch_fargotex_product_html",
        _fake_fetch_product,
    )

    def _raise_gallery_parser(html: str) -> list[dict]:
        raise ValueError("malformed gallery")

    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_gallery",
        _raise_gallery_parser,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.upholstery_providers.fargotex.parse_fargotex_product_variations",
        lambda html: [
            {
                "variation_id": "66747",
                "variant_name": "antracyt",
                "image": "https://fargotex.pl/uploads/noma.webp",
            }
        ],
    )

    result = await FargotexExternalUpholsteryProvider().search(q="noma", limit=7)

    assert len(result) == 1
    assert result[0]["code"] == "66747"
    assert result[0]["name"] == "Noma antracyt"


def _empty_product_page() -> str:
    return "<html></html>"


async def _fake_empty_product_fetch(product_url: str) -> str:
    return _empty_product_page()
