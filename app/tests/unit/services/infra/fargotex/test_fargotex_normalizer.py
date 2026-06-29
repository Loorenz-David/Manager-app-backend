import pytest

from beyo_manager.services.infra.fargotex.normalizer import normalize_fargotex_candidate


@pytest.mark.unit
def test_normalize_fargotex_candidate_full() -> None:
    result = normalize_fargotex_candidate(
        {
            "name": " Noma ",
            "code": "55379",
            "image": "https://fargotex.pl/wp-content/uploads/2025/03/nowa-noma.webp",
            "external_url": "https://fargotex.pl/produkt/noma/",
        }
    )

    assert result == {
        "client_id": None,
        "name": "Noma",
        "code": "55379",
        "image_url": "https://fargotex.pl/wp-content/uploads/2025/03/nowa-noma.webp",
        "external_url": "https://fargotex.pl/produkt/noma/",
        "favorite": None,
        "list_order": None,
        "current_stored_amount_meters": 0,
        "inventory_condition": "out_of_stock",
        "upholstery_category": None,
        "origin": "fargotex",
    }


@pytest.mark.unit
def test_normalize_fargotex_candidate_rejects_missing_required_fields() -> None:
    assert normalize_fargotex_candidate({"code": "55379", "image": "/noma.webp"}) is None
    assert normalize_fargotex_candidate({"name": "Noma", "image": "/noma.webp"}) is None
    assert normalize_fargotex_candidate({"name": "Noma", "code": "55379"}) is None
