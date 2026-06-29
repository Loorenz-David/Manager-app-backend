import pytest

from beyo_manager.services.infra.ohlssons_tyger.normalizer import (
    normalize_ohlssons_tyger_candidate,
)


@pytest.mark.unit
def test_normalize_ohlssons_tyger_candidate_full() -> None:
    result = normalize_ohlssons_tyger_candidate(
        {
            "name": " Viscose Deluxe ",
            "code": "ABC-123",
            "image": "/images/product.jpg",
            "detail_url": "https://www.ohlssonstyger.se/sv/artikel/viscose-deluxe",
        }
    )

    assert result == {
        "client_id": None,
        "name": "Viscose Deluxe",
        "code": "ABC-123",
        "image_url": "https://www.ohlssonstyger.se/images/product.jpg",
        "external_url": "https://www.ohlssonstyger.se/sv/artikel/viscose-deluxe",
        "favorite": None,
        "list_order": None,
        "current_stored_amount_meters": 0,
        "inventory_condition": "out_of_stock",
        "upholstery_category": None,
        "origin": "ohlssons_tyger",
    }


@pytest.mark.unit
def test_normalize_ohlssons_tyger_candidate_rejects_missing_name() -> None:
    assert normalize_ohlssons_tyger_candidate({"code": "ABC", "image": "/x.jpg"}) is None


@pytest.mark.unit
def test_normalize_ohlssons_tyger_candidate_rejects_missing_code() -> None:
    assert normalize_ohlssons_tyger_candidate({"name": "Viscose", "image": "/x.jpg"}) is None


@pytest.mark.unit
def test_normalize_ohlssons_tyger_candidate_rejects_missing_image() -> None:
    assert normalize_ohlssons_tyger_candidate({"name": "Viscose", "code": "ABC"}) is None


@pytest.mark.unit
def test_normalize_ohlssons_tyger_candidate_absolutizes_protocol_relative_image() -> None:
    result = normalize_ohlssons_tyger_candidate(
        {
            "name": "Viscose",
            "code": "ABC",
            "image": "//image.ohlssonstyger.se/example.jpg",
        }
    )

    assert result is not None
    assert result["image_url"] == "https://image.ohlssonstyger.se/example.jpg"
