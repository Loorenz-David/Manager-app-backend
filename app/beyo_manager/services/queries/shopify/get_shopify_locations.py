from __future__ import annotations

import logging

from sqlalchemy import select

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.shopify.results import ShopifyLocationResult, ShopifyLocationsShopResult
from beyo_manager.domain.shopify.scopes import has_all_required_scopes
from beyo_manager.domain.shopify.serializers import serialize_shopify_locations_response
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.inventory_client import fetch_shop_locations

logger = logging.getLogger(__name__)


async def get_shopify_locations(ctx: ServiceContext) -> dict:
    requested_ids = _parse_shop_integration_ids(ctx.query_params.get("shop_integration_ids"))
    if not requested_ids:
        raise ValidationError("Provide at least one shop_integration_id.")

    integrations = (
        await ctx.session.execute(
            select(ShopifyShopIntegration).where(
                ShopifyShopIntegration.workspace_id == ctx.workspace_id,
                ShopifyShopIntegration.client_id.in_(requested_ids),
                ShopifyShopIntegration.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    integrations_by_id = {integration.client_id: integration for integration in integrations}
    if any(shop_id not in integrations_by_id for shop_id in requested_ids):
        raise NotFound("Shopify shop integration not found.")

    shops: list[ShopifyLocationsShopResult] = []
    for shop_id in requested_ids:
        integration = integrations_by_id[shop_id]
        if integration.status != ShopifyIntegrationStatusEnum.ACTIVE:
            shops.append(
                ShopifyLocationsShopResult(
                    shop_integration_id=integration.client_id,
                    shop_domain=integration.shop_domain,
                    status="needs_reauth",
                    locations=[],
                )
            )
            continue
        if not has_all_required_scopes(("read_locations",), integration.granted_scopes or ()):
            shops.append(
                ShopifyLocationsShopResult(
                    shop_integration_id=integration.client_id,
                    shop_domain=integration.shop_domain,
                    status="needs_reauth",
                    locations=[],
                )
            )
            continue
        if not (integration.access_token_encrypted or "").strip():
            shops.append(
                ShopifyLocationsShopResult(
                    shop_integration_id=integration.client_id,
                    shop_domain=integration.shop_domain,
                    status="error",
                    locations=[],
                )
            )
            continue
        try:
            raw_locations = await fetch_shop_locations(
                shop_domain=integration.shop_domain,
                access_token_encrypted=integration.access_token_encrypted,
            )
        except Exception:
            logger.exception(
                "shopify_locations | fetch_failed | shop_integration_id=%s",
                integration.client_id,
            )
            shops.append(
                ShopifyLocationsShopResult(
                    shop_integration_id=integration.client_id,
                    shop_domain=integration.shop_domain,
                    status="error",
                    locations=[],
                )
            )
            continue
        shops.append(
            ShopifyLocationsShopResult(
                shop_integration_id=integration.client_id,
                shop_domain=integration.shop_domain,
                status="ok",
                locations=[
                    ShopifyLocationResult(
                        location_id=location["location_id"],
                        name=location["name"],
                        is_active=location["is_active"],
                    )
                    for location in raw_locations
                ],
            )
        )
    return serialize_shopify_locations_response(shops)


def _parse_shop_integration_ids(value: object) -> list[str]:
    if value is None:
        return []
    ids = [part.strip() for part in str(value).split(",") if part.strip()]
    return list(dict.fromkeys(ids))
