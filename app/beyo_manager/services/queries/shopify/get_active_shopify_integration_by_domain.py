from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration


async def get_active_shopify_integration_by_domain(
    session: AsyncSession,
    shop_domain: str,
) -> ShopifyShopIntegration | None:
    result = await session.execute(
        select(ShopifyShopIntegration).where(
            ShopifyShopIntegration.shop_domain == shop_domain,
            ShopifyShopIntegration.is_deleted.is_(False),
            ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE,
        )
    )
    return result.scalar_one_or_none()
