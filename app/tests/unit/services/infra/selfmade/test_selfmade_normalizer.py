from beyo_manager.services.infra.selfmade.normalizer import (
    extract_selfmade_code,
    normalize_selfmade_candidate,
)


def test_extract_selfmade_code_from_url_suffix() -> None:
    assert (
        extract_selfmade_code("https://www.selfmade.com/sv-se/denim-med-stretch-cobolt-10-5oz-460872/")
        == "460872"
    )
    assert extract_selfmade_code("https://www.selfmade.com/sv-se/no-code/") is None


def test_normalize_selfmade_candidate_parses_meter_price() -> None:
    result = normalize_selfmade_candidate(
        {
            "detail_url": "/sv-se/denim-med-stretch-cobolt-10-5oz-460872/",
            "name": "Denim med stretch cobolt",
            "image_url": "/media/denim.webp",
            "raw_price": "149,96 kr/m",
            "availability_labels": ["Online", "Butik"],
        }
    )

    assert result is not None
    assert result["origin"] == "selfmade"
    assert result["code"] == "460872"
    assert result["external_url"] == "https://www.selfmade.com/sv-se/denim-med-stretch-cobolt-10-5oz-460872/"
    assert result["image_url"] == "https://www.selfmade.com/media/denim.webp"
    assert result["price_amount"] == 149.96
    assert result["price_currency"] == "SEK"
    assert result["unit"] == "m"
    assert result["availability"] == "Online, Butik"


def test_normalize_selfmade_candidate_marks_non_meter_price() -> None:
    result = normalize_selfmade_candidate(
        {
            "detail_url": "https://www.selfmade.com/sv-se/jeanstrad-stark-vit-400m-123456/",
            "name": "Jeanstråd stark vit 400m",
            "image_url": "https://cdn.selfmade.com/thread.webp",
            "raw_price": "49,95 kr",
        }
    )

    assert result is not None
    assert result["price_amount"] == 49.95
    assert result["unit"] is None


def test_normalize_selfmade_candidate_rejects_missing_required_fields() -> None:
    assert normalize_selfmade_candidate({"name": "Denim", "image_url": "/x.webp"}) is None
    assert normalize_selfmade_candidate({"detail_url": "/sv-se/denim-123/", "image_url": "/x.webp"}) is None
    assert normalize_selfmade_candidate({"detail_url": "/sv-se/denim-123/", "name": "Denim"}) is None
