import pytest

from beyo_manager.services.infra.fargotex.client import fetch_fargotex_product_html


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_url",
    [
        "https://example.com/produkt/neon/",
        "https://fargotex.pl/not-a-product/neon/",
        "https://fargotex.pl:8443/produkt/neon/",
        "https://fargotex.pl/produkt/",
    ],
)
async def test_fetch_fargotex_product_html_rejects_urls_outside_product_boundary(
    product_url: str,
) -> None:
    with pytest.raises(ValueError, match="Invalid Fargotex product URL"):
        await fetch_fargotex_product_html(product_url)
