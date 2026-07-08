from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
)
from beyo_manager.domain.shopify.scopes import compare_requested_and_granted_scopes, normalize_scopes
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.infra.crypto.field_encryption import encrypt_field

_ACTIVE_LIKE_STATUSES = (
    ShopifyIntegrationStatusEnum.PENDING_INSTALL,
    ShopifyIntegrationStatusEnum.ACTIVE,
    ShopifyIntegrationStatusEnum.NEEDS_REAUTH,
    ShopifyIntegrationStatusEnum.SCOPES_OUTDATED,
    ShopifyIntegrationStatusEnum.WEBHOOKS_OUTDATED,
    ShopifyIntegrationStatusEnum.ERROR,
)


def _same_workspace_shop_rows_stmt(workspace_id: str, shop_domain: str) -> Select[tuple[ShopifyShopIntegration]]:
    return (
        select(ShopifyShopIntegration)
        .where(
            ShopifyShopIntegration.workspace_id == workspace_id,
            ShopifyShopIntegration.shop_domain == shop_domain,
        )
        .order_by(ShopifyShopIntegration.created_at.desc())
        .with_for_update()
    )


def _active_conflict_stmt(workspace_id: str, shop_domain: str) -> Select[tuple[ShopifyShopIntegration]]:
    return (
        select(ShopifyShopIntegration)
        .where(
            ShopifyShopIntegration.shop_domain == shop_domain,
            ShopifyShopIntegration.workspace_id != workspace_id,
            ShopifyShopIntegration.is_deleted.is_(False),
            ShopifyShopIntegration.status.in_(_ACTIVE_LIKE_STATUSES),
        )
        .with_for_update()
    )


async def link_or_update_shopify_shop_record(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_id: str,
    shop_domain: str,
    access_token: str,
    requested_scopes: tuple[str, ...],
    granted_scopes: tuple[str, ...],
    api_version: str,
    shop_name: str | None = None,
) -> ShopifyShopIntegration:
    now = datetime.now(timezone.utc)
    comparison = compare_requested_and_granted_scopes(requested_scopes, granted_scopes)
    status = (
        ShopifyIntegrationStatusEnum.SCOPES_OUTDATED
        if comparison.is_outdated
        else ShopifyIntegrationStatusEnum.ACTIVE
    )

    conflict = (
        await session.execute(_active_conflict_stmt(workspace_id=workspace_id, shop_domain=shop_domain))
    ).scalar_one_or_none()
    if conflict is not None:
        raise ConflictError("This Shopify shop is already linked to another workspace.")

    existing = (
        await session.execute(_same_workspace_shop_rows_stmt(workspace_id=workspace_id, shop_domain=shop_domain))
    ).scalars().first()

    if existing is None:
        integration = ShopifyShopIntegration(
            workspace_id=workspace_id,
            shop_domain=shop_domain,
            shop_name=shop_name,
            provider="shopify",
            status=status,
            access_token_encrypted=encrypt_field(access_token),
            granted_scopes=list(normalize_scopes(granted_scopes)),
            requested_scopes=list(normalize_scopes(requested_scopes)),
            api_version=api_version,
            installed_at=now,
            last_connected_at=now,
            created_by_id=user_id,
            updated_by_id=user_id,
            last_error_code=None,
            last_error_message=None,
            is_deleted=False,
            deleted_at=None,
            uninstalled_at=None,
        )
        session.add(integration)
        await session.flush()
        event_type = ShopifyIntegrationEventTypeEnum.INSTALL
        event_message = "Shopify shop linked successfully."
    else:
        integration = existing
        event_type = (
            ShopifyIntegrationEventTypeEnum.REAUTHORIZE
            if existing.installed_at is not None
            else ShopifyIntegrationEventTypeEnum.INSTALL
        )
        event_message = (
            "Shopify shop reauthorized successfully."
            if event_type == ShopifyIntegrationEventTypeEnum.REAUTHORIZE
            else "Shopify shop linked successfully."
        )
        integration.shop_name = shop_name or integration.shop_name
        integration.provider = "shopify"
        integration.status = status
        integration.access_token_encrypted = encrypt_field(access_token)
        integration.access_token_expires_at = None
        integration.granted_scopes = list(comparison.granted)
        integration.requested_scopes = list(comparison.requested)
        integration.api_version = api_version
        integration.installed_at = integration.installed_at or now
        integration.last_connected_at = now
        integration.last_error_code = None
        integration.last_error_message = None
        integration.updated_by_id = user_id
        integration.created_by_id = integration.created_by_id or user_id
        integration.is_deleted = False
        integration.deleted_at = None
        integration.uninstalled_at = None
        await session.flush()

    await create_shopify_integration_event(
        session,
        workspace_id=workspace_id,
        shop_integration_id=integration.client_id,
        event_type=event_type,
        severity=ShopifyIntegrationEventSeverityEnum.INFO,
        message=event_message,
        metadata_json={
            "shop_domain": shop_domain,
            "status": integration.status.value,
            "requested_scopes": list(comparison.requested),
            "granted_scopes": list(comparison.granted),
            "missing_scopes": list(comparison.missing),
            "extra_scopes": list(comparison.extra),
        },
        created_by_id=user_id,
    )
    return integration
