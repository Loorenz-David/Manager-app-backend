import pytest

from beyo_manager.services.infra.ohlssons_tyger.parser import (
    parse_ohlssons_tyger_detail,
    parse_ohlssons_tyger_listing_candidates,
)

_BASE_URL = "https://www.ohlssonstyger.se"


@pytest.mark.unit
def test_parse_listing_candidates_extracts_dedupes_and_limits() -> None:
    html = """
    <div>
      <a href="/sv/artikel/product-a">
        <img src="/images/a.jpg" />
      </a>
      <a href="/sv/artikel/product-a">Product A</a>
      <a href="https://www.ohlssonstyger.se/sv/artikel/product-b">Product B</a>
      <a href="/sv/kategori/not-a-product">Ignore</a>
    </div>
    """

    result = parse_ohlssons_tyger_listing_candidates(html, _BASE_URL, limit=1)

    assert result == [
        {
            "name": "Product A",
            "detail_url": "https://www.ohlssonstyger.se/sv/artikel/product-a",
            "image_url": "/images/a.jpg",
        }
    ]


@pytest.mark.unit
def test_parse_detail_extracts_name_code_and_image() -> None:
    html = """
    <html>
      <head>
        <meta property="og:image" content="https://image.ohlssonstyger.se/example.jpg" />
      </head>
      <body>
        <h1> Product Name </h1>
        <div>Artikelnummer: ABC-123</div>
      </body>
    </html>
    """

    result = parse_ohlssons_tyger_detail(
        html,
        "https://www.ohlssonstyger.se/sv/artikel/product-name",
        _BASE_URL,
    )

    assert result == {
        "name": "Product Name",
        "code": "ABC-123",
        "image": "https://image.ohlssonstyger.se/example.jpg",
        "detail_url": "https://www.ohlssonstyger.se/sv/artikel/product-name",
    }


@pytest.mark.unit
def test_parse_detail_falls_back_to_slug_code() -> None:
    html = """
    <html>
      <body>
        <h1>Product Name</h1>
        <img src="//image.ohlssonstyger.se/example.jpg" />
      </body>
    </html>
    """

    result = parse_ohlssons_tyger_detail(
        html,
        "https://www.ohlssonstyger.se/sv/artikel/example-product-123",
        _BASE_URL,
    )

    assert result is not None
    assert result["code"] == "example-product-123"
    assert result["image"] == "https://image.ohlssonstyger.se/example.jpg"
