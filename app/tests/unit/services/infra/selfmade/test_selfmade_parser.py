from beyo_manager.services.infra.selfmade.parser import (
    has_next_selfmade_page,
    parse_selfmade_listing_candidates,
    parse_selfmade_result_total,
)


def test_parse_selfmade_listing_candidates_extracts_listing_card() -> None:
    html = """
    <div class="card product-box box-minimal">
      <a class="product-card-link" href="/sv-se/denim-med-stretch-cobolt-10-5oz-460872/">
        <img class="product-image" data-src="/media/denim.webp" />
      </a>
      <div class="product-name">Denim med stretch cobolt</div>
      <span class="product-price">149,96 kr/m</span>
      <div class="product-location"><span class="marker">Online</span></div>
      <span class="product-variant-label">+ 15 Färger</span>
    </div>
    """

    assert parse_selfmade_listing_candidates(html) == [
        {
            "detail_url": "https://www.selfmade.com/sv-se/denim-med-stretch-cobolt-10-5oz-460872/",
            "name": "Denim med stretch cobolt",
            "image_url": "https://www.selfmade.com/media/denim.webp",
            "raw_price": "149,96 kr/m",
            "availability_labels": ["Online"],
            "variant_label": "+ 15 Färger",
        }
    ]


def test_parse_selfmade_listing_candidates_uses_current_discount_price() -> None:
    html = """
    <div class="card product-box box-minimal">
      <a class="product-card-link" href="/sv-se/denim-med-stretch-460872/">
        <img class="product-image" data-src="/media/denim.webp" />
      </a>
      <div class="product-name">Denim</div>
      <span class="product-price with-list-price">
        <span class="list-price">
          <span class="list-price-price">199,95 kr </span>
        </span>
        149,96 kr/m
      </span>
    </div>
    """

    result = parse_selfmade_listing_candidates(html)

    assert result[0]["raw_price"] == "149,96 kr/m"


def test_parse_selfmade_listing_candidates_supports_search_wrapper_card() -> None:
    html = """
    <div class="card product-box box-search">
      <a class="product-box--search-wrapper" href="/sv-se/jeanstrad-stark-vit-400m-123456/">
        <img class="product-image" src="//cdn.selfmade.com/thread.webp" />
        <div class="product-name">Jeanstråd stark vit 400m</div>
        <span class="product-price">49,95 kr</span>
      </a>
    </div>
    """

    result = parse_selfmade_listing_candidates(html)

    assert result[0]["detail_url"] == "https://www.selfmade.com/sv-se/jeanstrad-stark-vit-400m-123456/"
    assert result[0]["image_url"] == "https://cdn.selfmade.com/thread.webp"
    assert result[0]["raw_price"] == "49,95 kr"


def test_parse_selfmade_result_total() -> None:
    assert parse_selfmade_result_total('<input class="search-result-total" value="1 234" />') == 1234
    assert parse_selfmade_result_total('<span class="result-total-label">12 produkter</span>') == 12


def test_has_next_selfmade_page() -> None:
    assert has_next_selfmade_page('<li class="page-item page-next"><a href="?p=2">Nästa</a></li>') is True
    assert has_next_selfmade_page('<li class="page-item page-next disabled"></li>') is False
