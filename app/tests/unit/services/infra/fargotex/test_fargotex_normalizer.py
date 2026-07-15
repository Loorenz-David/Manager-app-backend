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


@pytest.mark.unit
def test_normalize_fargotex_candidate_preserves_variation_metadata() -> None:
    result = normalize_fargotex_candidate(
        {
            "name": "Neon antracyt",
            "code": 66747,
            "image": "/uploads/neon-01.webp",
            "external_url": "/produkt/neon/",
            "variant_name": "antracyt",
            "variation_id": 66747,
            "parent_name": "Neon",
            "sku": "074572c53b3f",
        }
    )

    assert result is not None
    assert result["code"] == "66747"
    assert result["variation_id"] == "66747"
    assert result["variant_name"] == "antracyt"
    assert result["parent_name"] == "Neon"
    assert result["sku"] == "074572c53b3f"
    assert result["image_url"] == "https://fargotex.pl/uploads/neon-01.webp"
    assert result["external_url"] == "https://fargotex.pl/produkt/neon/"


@pytest.mark.unit
def test_normalize_fargotex_candidate_omits_empty_optional_metadata() -> None:
    result = normalize_fargotex_candidate(
        {
            "name": "Neon",
            "code": "55379",
            "image": "/neon.webp",
            "variant_name": " ",
            "variation_id": None,
            "parent_name": "Neon",
            "sku": "",
        }
    )

    assert result is not None
    assert "variant_name" not in result
    assert "variation_id" not in result
    assert result["parent_name"] == "Neon"
    assert "sku" not in result


@pytest.mark.unit
def test_normalize_fargotex_candidate_preserves_gallery_metadata() -> None:
    result = normalize_fargotex_candidate(
        {
            "name": "Neon 01",
            "code": "53035-01",
            "image": "https://fargotex.pl/uploads/neon-01-w-1200.webp",
            "external_url": "https://fargotex.pl/produkt/neon/",
            "variant_name": "01",
            "gallery_code": "01",
            "gallery_position": 2,
            "parent_name": "Neon",
        }
    )

    assert result is not None
    assert result["code"] == "53035-01"
    assert result["variant_name"] == "01"
    assert result["gallery_code"] == "01"
    assert result["gallery_position"] == "2"
    assert result["parent_name"] == "Neon"
    assert "variation_id" not in result
    assert "sku" not in result
