import html as html_lib
import json

import pytest

from beyo_manager.services.infra.fargotex.parser import (
    has_next_fargotex_page,
    parse_fargotex_listing_candidates,
    parse_fargotex_product_gallery,
    parse_fargotex_product_variations,
)


def _variation_form(payload: list[dict]) -> str:
    encoded_payload = html_lib.escape(
        json.dumps(payload, ensure_ascii=False),
        quote=True,
    )
    return f'<form class="variations_form cart" data-product_variations="{encoded_payload}"></form>'


@pytest.mark.unit
def test_parse_fargotex_listing_candidates_extracts_expected_candidate() -> None:
    html = """
    <ul class="products">
      <li class="has-post-title product type-product post-55379 status-publish has-post-thumbnail product-type-variable">
        <figure class="post-image product-image">
          <a href="https://fargotex.pl/produkt/noma/">
            <img src="https://fargotex.pl/wp-content/uploads/2025/03/nowa-noma.webp" alt="Noma" />
          </a>
        </figure>
        <h3 class="woocommerce-loop-product__title product_title">
          <a href="https://fargotex.pl/produkt/noma/">Noma</a>
        </h3>
      </li>
    </ul>
    """

    assert parse_fargotex_listing_candidates(html) == [
        {
            "name": "Noma",
            "code": "55379",
            "image": "https://fargotex.pl/wp-content/uploads/2025/03/nowa-noma.webp",
            "external_url": "https://fargotex.pl/produkt/noma/",
        }
    ]


@pytest.mark.unit
def test_parse_fargotex_listing_candidates_falls_back_to_slug_code() -> None:
    html = """
    <ul class="products">
      <li class="product type-product">
        <a href="https://fargotex.pl/produkt/noma/">
          <img src="https://fargotex.pl/wp-content/uploads/2025/03/nowa-noma.webp" alt="Noma" />
        </a>
      </li>
    </ul>
    """

    result = parse_fargotex_listing_candidates(html)

    assert result[0]["code"] == "noma"


@pytest.mark.unit
def test_parse_fargotex_listing_candidates_dedupes_by_external_url() -> None:
    html = """
    <ul class="products">
      <li class="product type-product post-55379">
        <a href="https://fargotex.pl/produkt/noma/"><img src="/noma.webp" alt="Noma" /></a>
      </li>
      <li class="product type-product post-55379">
        <h3 class="woocommerce-loop-product__title product_title">
          <a href="https://fargotex.pl/produkt/noma/">Noma</a>
        </h3>
      </li>
    </ul>
    """

    result = parse_fargotex_listing_candidates(html)

    assert len(result) == 1


@pytest.mark.unit
def test_has_next_fargotex_page_detects_next_link() -> None:
    html = '<a href="https://fargotex.pl/kategoria-produktu/tkaniny-obiciowe/page/2/" class="number nextp">›</a>'
    assert has_next_fargotex_page(html) is True


@pytest.mark.unit
def test_has_next_fargotex_page_accepts_common_class_and_link_orders() -> None:
    assert has_next_fargotex_page(
        '<a class="page-numbers next" href="/kategoria-produktu/tkaniny-obiciowe/page/2/">Next</a>'
    ) is True
    assert has_next_fargotex_page(
        '<link href="/kategoria-produktu/tkaniny-obiciowe/page/2/" rel="next" />'
    ) is True


@pytest.mark.unit
def test_has_next_fargotex_page_false_without_next_link() -> None:
    assert has_next_fargotex_page("<html></html>") is False


@pytest.mark.unit
def test_parse_fargotex_product_variations_decodes_and_filters_payload() -> None:
    html = _variation_form(
        [
            {
                "variation_id": 66747,
                "sku": "shared-sku",
                "attributes": {"attribute_pa_kolory": "antracyt"},
                "variation_is_active": True,
                "variation_is_visible": True,
                "image": {
                    "full_src": "/uploads/antracyt-full.webp",
                    "url": "/uploads/antracyt-url.webp",
                    "src": "/uploads/antracyt-src.webp",
                },
            },
            {
                "variation_id": "66748",
                "sku": "shared-sku",
                "attributes": {"attribute_pa_kolory": "czerwony"},
                "variation_is_active": True,
                "variation_is_visible": True,
                "image": {"url": "/uploads/czerwony-url.webp"},
            },
            {
                "variation_id": "66749",
                "sku": "shared-sku",
                "attributes": {"attribute_pa_kolory": "pomarańcz"},
                "variation_is_active": True,
                "variation_is_visible": True,
                "image": {"src": "/uploads/pomarancz-src.webp"},
            },
            {
                "variation_id": "inactive",
                "sku": "shared-sku",
                "attributes": {"attribute_pa_kolory": "inactive"},
                "variation_is_active": False,
                "variation_is_visible": True,
            },
            {
                "variation_id": "invisible",
                "sku": "shared-sku",
                "attributes": {"attribute_pa_kolory": "invisible"},
                "variation_is_active": True,
                "variation_is_visible": False,
            },
            {
                "variation_id": "missing-attribute",
                "sku": "shared-sku",
                "attributes": {"attribute_pa_rozmiar": "large"},
            },
        ]
    )

    result = parse_fargotex_product_variations(html)

    assert [item["variation_id"] for item in result] == ["66747", "66748", "66749"]
    assert [item["code"] for item in result] == ["66747", "66748", "66749"]
    assert [item["variant_name"] for item in result] == [
        "antracyt",
        "czerwony",
        "pomarańcz",
    ]
    assert [item["sku"] for item in result] == ["shared-sku"] * 3
    assert [item["image"] for item in result] == [
        "https://fargotex.pl/uploads/antracyt-full.webp",
        "https://fargotex.pl/uploads/czerwony-url.webp",
        "https://fargotex.pl/uploads/pomarancz-src.webp",
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    "page_html",
    [
        "<html><body>simple product</body></html>",
        '<form class="variations_form cart" data-product_variations="not-json"></form>',
        '<form class="variations_form cart"></form>',
    ],
)
def test_parse_fargotex_product_variations_returns_empty_for_unsupported_pages(
    page_html: str,
) -> None:
    assert parse_fargotex_product_variations(page_html) == []


@pytest.mark.unit
def test_parse_fargotex_product_gallery_resolves_order_and_optional_fields() -> None:
    html = """
    <div class="woocommerce-product-gallery__wrapper">
      <div class="woocommerce-product-gallery__image" data-image-id="1001">
        <a href="/uploads/neon-parent.webp">
          <img data-large_image="/uploads/ignored-large.webp" src="/uploads/neon-parent-100x100.webp" alt="Neon" />
        </a>
      </div>
      <div class="woocommerce-product-gallery__image">
        <img data-large_image="/uploads/neon-01-w-1200.webp" data-src="/uploads/ignored.webp" src="/uploads/neon-01-w-100x100.webp" alt="Neon - obrazek 2" />
      </div>
      <div class="woocommerce-product-gallery__image">
        <img data-src="/uploads/49neon-03-w-1200.webp" src="/uploads/neon-03-w-100x100.webp" />
      </div>
      <div class="woocommerce-product-gallery__image">
        <img src="/uploads/neon-100x100.webp" />
      </div>
      <div class="woocommerce-product-gallery__image">
        <img src="/uploads/nebbia01-w-1200.jpg" />
      </div>
      <div class="woocommerce-product-gallery__image">
        <img src="/uploads/921nebbia05-w-1200.jpg" />
      </div>
      <div class="woocommerce-product-gallery__image"></div>
    </div>
    """

    result = parse_fargotex_product_gallery(html)

    assert [item["position"] for item in result] == [1, 2, 3, 4, 5, 6, 7]
    assert [item["is_main"] for item in result] == [True, False, False, False, False, False, False]
    assert [item["image_code"] for item in result] == ["", "01", "03", "", "01", "05", ""]
    assert [item["image_url"] for item in result] == [
        "https://fargotex.pl/uploads/neon-parent.webp",
        "https://fargotex.pl/uploads/neon-01-w-1200.webp",
        "https://fargotex.pl/uploads/49neon-03-w-1200.webp",
        "https://fargotex.pl/uploads/neon-100x100.webp",
        "https://fargotex.pl/uploads/nebbia01-w-1200.jpg",
        "https://fargotex.pl/uploads/921nebbia05-w-1200.jpg",
        "",
    ]
    assert result[1]["thumbnail_url"] == "https://fargotex.pl/uploads/neon-01-w-100x100.webp"
    assert result[0]["media_id"] == "1001"
    assert result[0]["alt"] == "Neon"
    assert result[-1]["alt"] == ""


@pytest.mark.unit
def test_parse_fargotex_product_gallery_is_empty_without_wrapper() -> None:
    assert parse_fargotex_product_gallery("<div class='product'></div>") == []


@pytest.mark.unit
def test_parse_fargotex_product_gallery_preserves_tulia_code_before_filename_suffix() -> None:
    html = """
    <div class="woocommerce-product-gallery__wrapper">
      <div class="woocommerce-product-gallery__image">
        <img src="/uploads/tulia-nowa-1.webp" />
      </div>
      <div class="woocommerce-product-gallery__image">
        <img src="/uploads/Tulia02_2.webp" />
      </div>
    </div>
    """

    result = parse_fargotex_product_gallery(html)

    assert result[0]["is_main"] is True
    assert result[0]["image_code"] == "1"
    assert result[1]["image_code"] == "02"


@pytest.mark.unit
def test_gallery_assets_are_not_assigned_to_semantic_variations() -> None:
    variation = parse_fargotex_product_variations(
        _variation_form(
            [
                {
                    "variation_id": 1,
                    "attributes": {"attribute_pa_kolory": "antracyt"},
                    "image": {},
                }
            ]
        )
    )[0]

    assert variation["variant_name"] == "antracyt"
    assert variation["image"] == ""
    assert parse_fargotex_product_gallery(
        '<div class="woocommerce-product-gallery__wrapper"><div class="woocommerce-product-gallery__image"><img src="/uploads/neon-01.webp"></div></div>'
    )[0]["image_code"] == "01"
