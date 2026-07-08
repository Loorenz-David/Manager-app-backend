import pytest

from beyo_manager.domain.shopify.shop_domains import is_valid_shop_domain, normalize_shop_domain
from beyo_manager.errors.validation import ValidationError


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("mystore", "mystore.myshopify.com"),
        ("mystore.myshopify.com", "mystore.myshopify.com"),
        ("https://MyStore.myshopify.com", "mystore.myshopify.com"),
        ("https://mystore.myshopify.com/admin?x=1", "mystore.myshopify.com"),
    ],
)
def test_normalize_shop_domain_accepts_supported_inputs(raw_value: str, expected: str) -> None:
    assert normalize_shop_domain(raw_value) == expected


@pytest.mark.parametrize(
    "raw_value",
    [
        "",
        "two.parts.store",
        "example.com",
        "my_store",
        "shop!.myshopify.com",
    ],
)
def test_normalize_shop_domain_rejects_invalid_values(raw_value: str) -> None:
    with pytest.raises(ValidationError):
        normalize_shop_domain(raw_value)


def test_is_valid_shop_domain_returns_boolean() -> None:
    assert is_valid_shop_domain("valid-shop") is True
    assert is_valid_shop_domain("invalid shop") is False
