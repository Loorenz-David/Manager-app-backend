from __future__ import annotations

from types import SimpleNamespace

import pytest

from beyo_manager.domain.images.enums import ImageStorageProviderEnum
from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError
from beyo_manager.services.tasks.shopify import _product_media_resolver as module


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, image):
        self.image = image

    async def execute(self, _statement):
        return _ScalarResult(self.image)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolver_composes_s3_public_url_at_worker_time(monkeypatch) -> None:
    image = SimpleNamespace(
        image_url="products/chair.webp",
        storage_provider=ImageStorageProviderEnum.S3,
    )
    storage = SimpleNamespace(
        public_url=lambda key: f"https://cdn.example.com/{key}"
    )
    monkeypatch.setattr(module, "get_storage_client", lambda: storage)

    media = await module.resolve_product_media(
        _Session(image),
        normalized_payload={
            "image": {"image_id": "img_1"},
            "image_alt_text": "Oak chair",
        },
    )

    assert media == [
        {
            "originalSource": "https://cdn.example.com/products/chair.webp",
            "mediaContentType": "IMAGE",
            "alt": "Oak chair",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider",
    [ImageStorageProviderEnum.EXTERNAL, ImageStorageProviderEnum.SHOPIFY],
)
async def test_resolver_uses_external_provider_url_verbatim(provider) -> None:
    url = "https://images.example.com/chair.webp"
    image = SimpleNamespace(image_url=url, storage_provider=provider)

    media = await module.resolve_product_media(
        _Session(image),
        normalized_payload={"image": {"image_id": "img_1"}},
    )

    assert media[0]["originalSource"] == url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolver_rejects_non_https_url() -> None:
    with pytest.raises(
        ShopifyGraphQLNonRetryableError,
        match="absolute HTTPS URL",
    ):
        await module.resolve_product_media(
            _Session(None),
            normalized_payload={
                "image": {"image_url": "http://images.example.com/chair.webp"}
            },
        )
