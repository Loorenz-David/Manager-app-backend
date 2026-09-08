import pytest

from beyo_manager.services.infra.nevotex.parser import parse_nevotex_search_results

# Captured verbatim from
# https://nevotex.se/service-pages/product-and-content-search-results?...&eq=1008336
_SINGLE_RESULT_HTML = """<section data-swift-gridrow="1Column">
<div data-swift-container class="grid"><div data-swift-gridcolumn data-dw-itemtype="swift-v2_app" id="19264"><li class="dropdown-item d-flex" onclick="swift.Typeahead.selectSuggestion(this);" data-param="ProductId" data-selected-details-page="/Default.aspx?ID=11591&GroupId=GROUP318&ProductId=1008301&VariantID=VARGRP249_1008336" data-paramvalue="1008301"><div class="d-flex"><div class="d-flex" href="/produkter/bekladnadsmaterial/mobeltyger/alla-mobeltyger/eros/1008336"><img class="mx-2"
src="/admin/public/getimage.ashx?image=%2FFiles%2FImages%2Fproduktbilder%2F1008336.jpg&width=45&height=36&format=webp&Crop=5&fillcanvas=true&Compression=75"
height="45"
width="36"
alt="Tyg Eros 36 Light brown ">
<div><span class="js-suggestion flex-fill text-break" data-suggestion-value="">tyg eros 36 light brown </span></div></div><div class="d-flex"><a class="btn btn-primary dw-mod"
title="Visa"
href="/produkter/bekladnadsmaterial/mobeltyger/alla-mobeltyger/eros/1008336">
Visa
</a></div></div></li><li class="dropdown-item text-center p-2 text-wrap" id="ViewAllProductResults" onclick="swift.Typeahead.selectSuggestion(this);" data-all-results-page="/soekresultat"><span class="text-break"><mark> "<span class="js-suggestion">1008336</span>"</mark></span></li></div></div></section>"""

# Captured verbatim for a query with no hits.
_NO_RESULTS_HTML = """<section data-swift-gridrow="1Column">
<div data-swift-container class="grid"><div data-swift-gridcolumn id="19264"><li class="dropdown-item text-center text-wrap px-1" id="NoProductResults">Vi hittade inga produkter för<mark> "<span class="js-suggestion">zzzzqqq</span>"</mark></li></div></div></section>"""


def _product_row(*, product_id: str, variant_id: str, article: str, name: str) -> str:
    details = f"/Default.aspx?ID=11591&GroupId=GROUP318&ProductId={product_id}"
    if variant_id:
        details += f"&VariantID={variant_id}"
    return (
        f'<li data-param="ProductId" data-selected-details-page="{details}" '
        f'data-paramvalue="{product_id}">'
        f'<img src="/admin/public/getimage.ashx?image=%2FFiles%2F{article}.jpg" alt="{name}">'
        f'<span class="js-suggestion">{name.lower()}</span>'
        f'<a title="Visa" href="/produkter/mobeltyger/eros/{article}">Visa</a>'
        "</li>"
    )


@pytest.mark.unit
def test_parses_exact_article_number_result() -> None:
    result = parse_nevotex_search_results(_SINGLE_RESULT_HTML)

    assert result == [
        {
            "productId": "1008301",
            "variantId": "VARGRP249_1008336",
            "number": "1008336",
            "name": "Tyg Eros 36 Light brown",
            "image": (
                "/admin/public/getimage.ashx"
                "?image=%2FFiles%2FImages%2Fproduktbilder%2F1008336.jpg"
                "&width=45&height=36&format=webp&Crop=5&fillcanvas=true&Compression=75"
            ),
            "url": "/produkter/bekladnadsmaterial/mobeltyger/alla-mobeltyger/eros/1008336",
        }
    ]


@pytest.mark.unit
def test_article_number_is_the_variant_not_the_base_product_id() -> None:
    [product] = parse_nevotex_search_results(_SINGLE_RESULT_HTML)

    assert product["number"] == "1008336"
    assert product["productId"] == "1008301"
    assert product["number"] != product["productId"]


@pytest.mark.unit
def test_name_prefers_image_alt_over_lowercased_suggestion_text() -> None:
    [product] = parse_nevotex_search_results(_SINGLE_RESULT_HTML)

    assert product["name"] == "Tyg Eros 36 Light brown"


@pytest.mark.unit
def test_ignores_the_view_all_products_row() -> None:
    result = parse_nevotex_search_results(_SINGLE_RESULT_HTML)

    assert len(result) == 1
    assert all(product["number"] != "" for product in result)


@pytest.mark.unit
def test_zero_results_returns_empty_list() -> None:
    assert parse_nevotex_search_results(_NO_RESULTS_HTML) == []


@pytest.mark.unit
def test_parses_multiple_product_results() -> None:
    html = "<section>" + "".join(
        [
            _product_row(
                product_id="1008301",
                variant_id="VARGRP249_1008302",
                article="1008302",
                name="Tyg Eros 2 Midnight",
            ),
            _product_row(
                product_id="1008301",
                variant_id="VARGRP249_1008303",
                article="1008303",
                name="Tyg Eros 3 Forest",
            ),
        ]
    ) + "</section>"

    result = parse_nevotex_search_results(html)

    assert [product["number"] for product in result] == ["1008302", "1008303"]
    assert [product["productId"] for product in result] == ["1008301", "1008301"]
    assert [product["variantId"] for product in result] == [
        "VARGRP249_1008302",
        "VARGRP249_1008303",
    ]
    assert [product["name"] for product in result] == [
        "Tyg Eros 2 Midnight",
        "Tyg Eros 3 Forest",
    ]


@pytest.mark.unit
def test_limit_truncates_results() -> None:
    html = "<section>" + "".join(
        _product_row(
            product_id="100830{index}".format(index=index),
            variant_id="",
            article="100830{index}".format(index=index),
            name=f"Tyg {index}",
        )
        for index in range(4)
    ) + "</section>"

    assert len(parse_nevotex_search_results(html, limit=2)) == 2
    assert len(parse_nevotex_search_results(html, limit=None)) == 4


@pytest.mark.unit
def test_product_without_variant_falls_back_to_product_id() -> None:
    html = _product_row(
        product_id="4012800",
        variant_id="",
        article="4012800",
        name="Knappform A28",
    )

    [product] = parse_nevotex_search_results(html)

    assert product["variantId"] == ""
    assert product["number"] == "4012800"
    assert product["productId"] == "4012800"


@pytest.mark.unit
def test_non_numeric_variant_suffix_falls_back_to_url_article_number() -> None:
    html = (
        '<li data-param="ProductId" data-paramvalue="1008301" '
        'data-selected-details-page="/Default.aspx?ProductId=1008301&VariantID=VARGRP249">'
        '<a title="Visa" href="/produkter/mobeltyger/eros/1008336">Visa</a>'
        "</li>"
    )

    [product] = parse_nevotex_search_results(html)

    assert product["variantId"] == "VARGRP249"
    assert product["number"] == "1008336"


@pytest.mark.unit
def test_row_missing_optional_markup_yields_empty_fields_without_raising() -> None:
    html = '<li data-param="ProductId" data-paramvalue="1008301"></li>'

    [product] = parse_nevotex_search_results(html)

    assert product == {
        "productId": "1008301",
        "variantId": "",
        "number": "1008301",
        "name": "",
        "image": "",
        "url": "",
    }


@pytest.mark.unit
def test_unclosed_product_row_is_still_captured() -> None:
    html = (
        '<li data-param="ProductId" data-paramvalue="1"><img alt="Tyg A" src="/a.jpg">'
        '<li data-param="ProductId" data-paramvalue="2"><img alt="Tyg B" src="/b.jpg">'
    )

    result = parse_nevotex_search_results(html)

    assert [product["name"] for product in result] == ["Tyg A", "Tyg B"]


@pytest.mark.unit
def test_html_without_any_product_rows_returns_empty_list() -> None:
    assert parse_nevotex_search_results("<html><body><p>Ingen</p></body></html>") == []
