import pytest

from beyo_manager.services.infra.nevotex.normalizer import (
    normalize_nevotex_candidate,
    normalize_nevotex_candidates,
)


@pytest.mark.unit
def test_normalize_nevotex_candidate_full() -> None:
    raw = {
        "productId": "1000401",
        "name": "Tyg Afrodite 2 Midnight ",
        "number": "1000402",
        "image": "%2fFiles%2fImages%2fproduktbilder%2f1000402.jpg",
        "url": "/produkter/tyg-afrodite-2-midnight",
    }

    result = normalize_nevotex_candidate(raw)

    assert result is not None
    assert result["client_id"] is None
    assert result["name"] == "Tyg Afrodite 2 Midnight"
    assert result["code"] == "1000402"
    assert result["image_url"] == "https://nevotex.se/Files/Images/produktbilder/1000402.jpg"
    assert result["external_url"] == "https://nevotex.se/produkter/tyg-afrodite-2-midnight"
    assert result["favorite"] is None
    assert result["list_order"] is None
    assert result["current_stored_amount_meters"] == 0
    assert result["inventory_condition"] == "out_of_stock"
    assert result["upholstery_category"] is None
    assert result["origin"] == "nevotex"


@pytest.mark.unit
def test_normalize_nevotex_candidate_decodes_and_absolutizes_image_url() -> None:
    result = normalize_nevotex_candidate(
        {
            "name": "Tyg X",
            "number": "12345",
            "image": "%2fFiles%2fImages%2fproduktbilder%2f12345.jpg",
        }
    )

    assert result is not None
    assert result["image_url"] == "https://nevotex.se/Files/Images/produktbilder/12345.jpg"


@pytest.mark.unit
def test_normalize_nevotex_candidate_handles_missing_external_url() -> None:
    result = normalize_nevotex_candidate(
        {
            "name": "Tyg X",
            "number": "12345",
            "image": "%2fFiles%2fImages%2fproduktbilder%2f12345.jpg",
        }
    )

    assert result is not None
    assert result["external_url"] is None


@pytest.mark.unit
def test_normalize_nevotex_candidate_skips_missing_required_fields() -> None:
    assert normalize_nevotex_candidate({"name": "", "number": "1000402", "image": "%2f1.jpg"}) is None
    assert normalize_nevotex_candidate({"name": "Tyg X", "number": "", "image": "%2f1.jpg"}) is None
    assert normalize_nevotex_candidate({"name": "Tyg X", "number": "1000402", "image": ""}) is None


@pytest.mark.unit
def test_normalize_nevotex_candidates_filters_malformed_products() -> None:
    products = [
        {"name": "Good", "number": "111", "image": "%2fa.jpg"},
        {"name": "", "number": "222", "image": "%2fb.jpg"},
        {"name": "Also Good", "number": "333", "image": "%2fc.jpg"},
    ]

    results = normalize_nevotex_candidates(products)

    assert len(results) == 2
    assert results[0]["code"] == "111"
    assert results[1]["code"] == "333"


@pytest.mark.unit
def test_normalize_nevotex_candidates_empty_list() -> None:
    assert normalize_nevotex_candidates([]) == []


@pytest.mark.unit
def test_normalize_nevotex_candidate_from_swift_search_row() -> None:
    raw = {
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

    result = normalize_nevotex_candidate(raw)

    assert result is not None
    assert result["name"] == "Tyg Eros 36 Light brown"
    assert result["code"] == "1008336"
    assert result["image_url"] == (
        "https://nevotex.se/admin/public/getimage.ashx"
        "?image=%2FFiles%2FImages%2Fproduktbilder%2F1008336.jpg"
        "&width=45&height=36&format=webp&Crop=5&fillcanvas=true&Compression=75"
    )
    assert result["external_url"] == (
        "https://nevotex.se/produkter/bekladnadsmaterial/mobeltyger/alla-mobeltyger/eros/1008336"
    )
    assert result["origin"] == "nevotex"


@pytest.mark.unit
def test_normalize_nevotex_candidate_keeps_encoded_image_query_intact() -> None:
    result = normalize_nevotex_candidate(
        {
            "name": "Tyg X",
            "number": "12345",
            "image": "/admin/public/getimage.ashx?image=%2FFiles%2F12345.jpg&width=45",
        }
    )

    assert result is not None
    assert result["image_url"] == (
        "https://nevotex.se/admin/public/getimage.ashx?image=%2FFiles%2F12345.jpg&width=45"
    )


@pytest.mark.unit
def test_normalize_nevotex_candidate_skips_non_string_required_fields() -> None:
    assert normalize_nevotex_candidate({"name": 123, "number": "1000402", "image": "%2f1.jpg"}) is None
    assert normalize_nevotex_candidate({"name": "Tyg X", "number": 456, "image": "%2f1.jpg"}) is None
    assert normalize_nevotex_candidate({"name": "Tyg X", "number": "1000402", "image": ["bad"]}) is None
