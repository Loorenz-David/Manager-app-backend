from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.shopify.product_sync_payloads import build_normalized_product_sync_payload
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.commands.shopify.requests.process_shopify_products_request import (
    ProcessShopifyProductItemRequest,
    ProcessShopifyProductsRequest,
)


async def resolve_and_normalize_sync_targets(
    session: AsyncSession,
    *,
    workspace_id: str,
    request: ProcessShopifyProductsRequest,
) -> list[tuple[ShopifyShopIntegration, ProcessShopifyProductItemRequest, dict]]:
    integrations = (
        await session.execute(
            select(ShopifyShopIntegration)
            .where(
                ShopifyShopIntegration.workspace_id == workspace_id,
                ShopifyShopIntegration.is_deleted.is_(False),
                ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE,
            )
            .order_by(ShopifyShopIntegration.created_at.desc())
        )
    ).scalars().all()

    active_by_id = {integration.client_id: integration for integration in integrations}
    if not active_by_id:
        raise ValidationError("No active Shopify shop integrations found for this workspace.")

    targets: list[tuple[ShopifyShopIntegration, ProcessShopifyProductItemRequest, dict]] = []
    for item in request.items:
        normalized_payload = build_normalized_product_sync_payload(item.model_dump())
        raw_target_ids = item.target_shop_integration_ids or list(active_by_id)
        target_ids = list(dict.fromkeys(raw_target_ids))  # dedupe, preserve order
        missing_ids = [shop_id for shop_id in target_ids if shop_id not in active_by_id]
        if missing_ids:
            raise NotFound("Shopify shop integration not found.")
        for shop_id in target_ids:
            targets.append((active_by_id[shop_id], item, normalized_payload))
    return targets
