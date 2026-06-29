import pytest

from beyo_manager.services.infra.fargotex.parser import (
    has_next_fargotex_page,
    parse_fargotex_listing_candidates,
)


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
def test_has_next_fargotex_page_false_without_next_link() -> None:
    assert has_next_fargotex_page("<html></html>") is False
