from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator, model_validator
from sqlalchemy import select

from beyo_manager.domain.shopify.customer_lookup import (
    filter_shopify_order_line_item_exact_matches,
    normalize_shopify_customer_lookup_result,
)
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.shopify.scopes import has_all_required_scopes
from beyo_manager.errors.external_service import ExternalServiceError, ShopifyGraphQLError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.product_identity_client import fetch_shopify_orders_by_product_identity

IdentityType = Literal["sku", "barcode"]
_REQUIRED_SCOPES: tuple[str, ...] = ("read_orders", "read_products", "read_customers")


class ShopifyProductIdentityLookupRequest(BaseModel):
    article_number: str | None = None
    sku: str | None = None

    @field_validator("article_number", "sku", mode="before")
    @classmethod
    def _trim_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _require_identity(self) -> "ShopifyProductIdentityLookupRequest":
        if self.article_number is None and self.sku is None:
            raise ValueError("At least one of sku or article_number is required.")
        return self


def parse_shopify_product_identity_lookup_request(data: dict) -> ShopifyProductIdentityLookupRequest:
    try:
        return ShopifyProductIdentityLookupRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        prefix = f"{field}: " if field else ""
        raise ValidationError(f"{prefix}{first_error['msg']}") from exc


async def lookup_shopify_customers_by_product_identity(ctx: ServiceContext) -> dict:
    request = parse_shopify_product_identity_lookup_request(ctx.incoming_data)
    query = (
        select(ShopifyShopIntegration)
        .where(
            ShopifyShopIntegration.workspace_id == ctx.workspace_id,
            ShopifyShopIntegration.is_deleted.is_(False),
            ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE,
        )
        .order_by(ShopifyShopIntegration.created_at.desc())
    )
    integrations = (await ctx.session.execute(query)).scalars().all()

    all_matches = []
    failed_shops: list[dict[str, str]] = []
    attempted_shop_ids: list[str] = []

    for integration in integrations:
        if not has_all_required_scopes(_REQUIRED_SCOPES, integration.granted_scopes or ()):
            failed_shops.append(
                {
                    "shop_integration_id": integration.client_id,
                    "shop_domain": integration.shop_domain,
                    "error_code": "missing_required_scope",
                }
            )
            continue

        if not (integration.access_token_encrypted or "").strip():
            failed_shops.append(
                {
                    "shop_integration_id": integration.client_id,
                    "shop_domain": integration.shop_domain,
                    "error_code": "missing_access_token",
                }
            )
            continue

        attempted_shop_ids.append(integration.client_id)
        try:
            all_matches.extend(await _lookup_customer_matches_for_shop(integration=integration, request=request))
        except ShopifyGraphQLError as exc:
            failed_shops.append(
                {
                    "shop_integration_id": integration.client_id,
                    "shop_domain": integration.shop_domain,
                    "error_code": exc.error_code,
                }
            )

    customer_matches = [asdict(match) for match in all_matches]
    graphql_failed_ids = {
        item["shop_integration_id"]
        for item in failed_shops
        if item["error_code"] not in {"missing_required_scope", "missing_access_token"}
    }
    if attempted_shop_ids and not customer_matches and graphql_failed_ids == set(attempted_shop_ids):
        raise ExternalServiceError("All Shopify shop lookups failed.")
    return {
        "customer_matches": customer_matches,
        "failed_shops": failed_shops,
    }


async def _lookup_customer_matches_for_shop(
    *,
    integration: ShopifyShopIntegration,
    request: ShopifyProductIdentityLookupRequest,
) -> list:
    if request.sku is not None:
        sku_matches = await _lookup_customer_matches_for_identity(
            integration=integration,
            identity_type="sku",
            identity_value=request.sku,
        )
        if sku_matches:
            return sku_matches
        if request.article_number is None:
            return []

    if request.article_number is not None:
        return await _lookup_customer_matches_for_identity(
            integration=integration,
            identity_type="barcode",
            identity_value=request.article_number,
        )

    return []


async def _lookup_customer_matches_for_identity(
    *,
    integration: ShopifyShopIntegration,
    identity_type: IdentityType,
    identity_value: str,
) -> list:
    order_nodes = await fetch_shopify_orders_by_product_identity(
        shop_domain=integration.shop_domain,
        access_token_encrypted=integration.access_token_encrypted,
        identity_type=identity_type,
        identity_value=identity_value,
    )
    exact_matches = filter_shopify_order_line_item_exact_matches(
        order_nodes,
        identity_type=identity_type,
        identity_value=identity_value,
    )
    return [
        normalize_shopify_customer_lookup_result(
            order_node,
            shop_integration_id=integration.client_id,
            shop_domain=integration.shop_domain,
            match_type=identity_type,
            matched_value=identity_value,
        )
        for order_node in exact_matches
    ]
