from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.images.enums import ImageStorageProviderEnum
from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError
from beyo_manager.models.tables.images.image import Image
from beyo_manager.services.infra.storage import get_storage_client


async def resolve_product_media(
    session: AsyncSession,
    *,
    normalized_payload: dict,
) -> list[dict] | None:
    image_reference = normalized_payload.get("image")
    if not isinstance(image_reference, dict):
        return None

    image_url = _clean_str(image_reference.get("image_url"))
    image_id = _clean_str(image_reference.get("image_id"))
    if image_id is not None:
        image = (
            await session.execute(
                select(Image).where(
                    Image.client_id == image_id,
                    Image.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if image is None:
            raise ShopifyGraphQLNonRetryableError(
                "Shopify product image could not be resolved.",
                error_code="product_image_unresolved",
            )
        if image.storage_provider == ImageStorageProviderEnum.S3:
            image_url = get_storage_client().public_url(image.image_url)
        else:
            image_url = image.image_url

    if not _is_absolute_https_url(image_url):
        raise ShopifyGraphQLNonRetryableError(
            "Shopify product image must use an absolute HTTPS URL.",
            error_code="invalid_product_image_url",
        )

    media = {
        "originalSource": image_url,
        "mediaContentType": "IMAGE",
    }
    alt_text = _clean_str(normalized_payload.get("image_alt_text"))
    if alt_text is not None:
        media["alt"] = alt_text
    return [media]


def _is_absolute_https_url(value: str | None) -> bool:
    if value is None:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
