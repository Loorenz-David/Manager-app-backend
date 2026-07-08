from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookPayloadFormatEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.domain.shopify.scopes import has_all_required_scopes
from beyo_manager.domain.shopify.webhook_registry import (
    SHOPIFY_WEBHOOK_CALLBACK_PATH,
    SHOPIFY_WEBHOOK_REGISTRY,
)
from beyo_manager.errors.external_service import ShopifyGraphQLError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.webhook_subscription_client import (
    RemoteWebhookSubscription,
    create_remote_webhook_subscription,
    delete_remote_webhook_subscription,
    list_remote_webhook_subscriptions,
)

logger = logging.getLogger(__name__)

_SYNCABLE_INTEGRATION_STATUSES = {
    ShopifyIntegrationStatusEnum.PENDING_INSTALL,
    ShopifyIntegrationStatusEnum.ACTIVE,
    ShopifyIntegrationStatusEnum.NEEDS_REAUTH,
    ShopifyIntegrationStatusEnum.SCOPES_OUTDATED,
    ShopifyIntegrationStatusEnum.WEBHOOKS_OUTDATED,
    ShopifyIntegrationStatusEnum.ERROR,
}

MISSING_REQUIRED_SCOPE_ERROR_CODE = "missing_required_scope"


class SyncShopifyWebhookSubscriptionsForShopRequest(BaseModel):
    shop_integration_id: str

    @field_validator("shop_integration_id")
    @classmethod
    def _required_string_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank.")
        return value


def parse_sync_shopify_webhook_subscriptions_for_shop_request(
    data: dict,
) -> SyncShopifyWebhookSubscriptionsForShopRequest:
    try:
        return SyncShopifyWebhookSubscriptionsForShopRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def sync_shopify_webhook_subscriptions_for_shop(ctx: ServiceContext) -> dict:
    request = parse_sync_shopify_webhook_subscriptions_for_shop_request(ctx.incoming_data)
    integration = await _load_shopify_integration(ctx, request.shop_integration_id)
    callback_url = _build_callback_url()
    now = datetime.now(timezone.utc)

    remote_subscriptions = await list_remote_webhook_subscriptions(
        shop_domain=integration.shop_domain,
        access_token_encrypted=integration.access_token_encrypted or "",
    )
    local_rows = await _load_local_subscription_rows(ctx, integration.client_id)

    backend_remote_by_topic: dict[str, list[RemoteWebhookSubscription]] = {}
    for remote_subscription in remote_subscriptions:
        if remote_subscription.callback_url == callback_url:
            backend_remote_by_topic.setdefault(remote_subscription.topic, []).append(remote_subscription)

    created_topics: list[str] = []
    removed_topics: list[str] = []
    verified_topics: list[str] = []
    missing_scope_topics: list[str] = []
    failed_topics: list[str] = []

    async with maybe_begin(ctx.session):
        for definition in SHOPIFY_WEBHOOK_REGISTRY:
            local_row = local_rows.get(definition.topic)
            owned_remote = backend_remote_by_topic.get(definition.topic, [])
            required_scopes = tuple(definition.required_scopes)
            has_required_scopes = has_all_required_scopes(
                definition.required_scopes,
                tuple(integration.granted_scopes or ()),
            )

            if not definition.enabled:
                if local_row is not None and local_row.status == ShopifyWebhookSubscriptionStatusEnum.REMOVED:
                    continue
                if owned_remote:
                    try:
                        for remote_subscription in owned_remote:
                            await delete_remote_webhook_subscription(
                                shop_domain=integration.shop_domain,
                                access_token_encrypted=integration.access_token_encrypted or "",
                                remote_subscription_id=remote_subscription.id,
                            )
                        await _upsert_local_subscription_row(
                            ctx,
                            local_row=local_row,
                            integration=integration,
                            topic=definition.topic,
                            callback_url=callback_url,
                            required_scopes=required_scopes,
                            status=ShopifyWebhookSubscriptionStatusEnum.REMOVED,
                            remote_subscription_id=None,
                            installed_at=local_row.installed_at if local_row is not None else None,
                            last_verified_at=now,
                            last_install_attempt_at=local_row.last_install_attempt_at if local_row is not None else None,
                            last_error_code=None,
                            last_error_message=None,
                        )
                        removed_topics.append(definition.topic)
                    except ShopifyGraphQLError as exc:
                        failed_topics.append(definition.topic)
                        await _mark_topic_failed(
                            ctx,
                            local_row=local_row,
                            integration=integration,
                            topic=definition.topic,
                            callback_url=callback_url,
                            required_scopes=required_scopes,
                            remote_subscription_id=_first_remote_id(owned_remote),
                            last_verified_at=now,
                            last_install_attempt_at=now,
                            error_code=exc.error_code,
                            error_message=str(exc),
                        )
                elif local_row is not None:
                    await _upsert_local_subscription_row(
                        ctx,
                        local_row=local_row,
                        integration=integration,
                        topic=definition.topic,
                        callback_url=callback_url,
                        required_scopes=required_scopes,
                        status=ShopifyWebhookSubscriptionStatusEnum.REMOVED,
                        remote_subscription_id=None,
                        installed_at=local_row.installed_at,
                        last_verified_at=now,
                        last_install_attempt_at=local_row.last_install_attempt_at,
                        last_error_code=None,
                        last_error_message=None,
                    )
                    removed_topics.append(definition.topic)
                continue

            if not has_required_scopes:
                missing_scope_topics.append(definition.topic)
                _log_missing_scope(integration.shop_domain, definition.topic, required_scopes, integration.granted_scopes)
                await _upsert_local_subscription_row(
                    ctx,
                    local_row=local_row,
                    integration=integration,
                    topic=definition.topic,
                    callback_url=callback_url,
                    required_scopes=required_scopes,
                    status=ShopifyWebhookSubscriptionStatusEnum.FAILED,
                    remote_subscription_id=_first_remote_id(owned_remote),
                    installed_at=local_row.installed_at if local_row is not None else None,
                    last_verified_at=now,
                    last_install_attempt_at=now,
                    last_error_code=MISSING_REQUIRED_SCOPE_ERROR_CODE,
                    last_error_message="Missing required Shopify scopes for webhook subscription.",
                )
                continue

            if owned_remote:
                remote_subscription = owned_remote[0]
                await _upsert_local_subscription_row(
                    ctx,
                    local_row=local_row,
                    integration=integration,
                    topic=definition.topic,
                    callback_url=callback_url,
                    required_scopes=required_scopes,
                    status=ShopifyWebhookSubscriptionStatusEnum.ACTIVE,
                    remote_subscription_id=remote_subscription.id,
                    installed_at=local_row.installed_at or now if local_row is not None else now,
                    last_verified_at=now,
                    last_install_attempt_at=local_row.last_install_attempt_at if local_row is not None else None,
                    last_error_code=None,
                    last_error_message=None,
                )
                verified_topics.append(definition.topic)
                continue

            try:
                remote_subscription = await create_remote_webhook_subscription(
                    shop_domain=integration.shop_domain,
                    access_token_encrypted=integration.access_token_encrypted or "",
                    topic=definition.topic,
                    callback_url=callback_url,
                    payload_format=definition.payload_format,
                )
                await _upsert_local_subscription_row(
                    ctx,
                    local_row=local_row,
                    integration=integration,
                    topic=definition.topic,
                    callback_url=callback_url,
                    required_scopes=required_scopes,
                    status=ShopifyWebhookSubscriptionStatusEnum.ACTIVE,
                    remote_subscription_id=remote_subscription.id,
                    installed_at=now,
                    last_verified_at=now,
                    last_install_attempt_at=now,
                    last_error_code=None,
                    last_error_message=None,
                )
                created_topics.append(definition.topic)
            except ShopifyGraphQLError as exc:
                failed_topics.append(definition.topic)
                await _mark_topic_failed(
                    ctx,
                    local_row=local_row,
                    integration=integration,
                    topic=definition.topic,
                    callback_url=callback_url,
                    required_scopes=required_scopes,
                    remote_subscription_id=None,
                    last_verified_at=now,
                    last_install_attempt_at=now,
                    error_code=exc.error_code,
                    error_message=str(exc),
                )

        registry_topics = {definition.topic for definition in SHOPIFY_WEBHOOK_REGISTRY}
        for topic, owned_remote in backend_remote_by_topic.items():
            if topic in registry_topics:
                continue
            local_row = local_rows.get(topic)
            if local_row is not None and local_row.status == ShopifyWebhookSubscriptionStatusEnum.REMOVED:
                continue
            try:
                for remote_subscription in owned_remote:
                    await delete_remote_webhook_subscription(
                        shop_domain=integration.shop_domain,
                        access_token_encrypted=integration.access_token_encrypted or "",
                        remote_subscription_id=remote_subscription.id,
                    )
                await _upsert_local_subscription_row(
                    ctx,
                    local_row=local_row,
                    integration=integration,
                    topic=topic,
                    callback_url=callback_url,
                    required_scopes=tuple(local_row.required_scopes or ()),
                    status=ShopifyWebhookSubscriptionStatusEnum.REMOVED,
                    remote_subscription_id=None,
                    installed_at=local_row.installed_at if local_row is not None else None,
                    last_verified_at=now,
                    last_install_attempt_at=local_row.last_install_attempt_at if local_row is not None else None,
                    last_error_code=None,
                    last_error_message=None,
                )
                removed_topics.append(topic)
            except ShopifyGraphQLError as exc:
                failed_topics.append(topic)
                await _mark_topic_failed(
                    ctx,
                    local_row=local_row,
                    integration=integration,
                    topic=topic,
                    callback_url=callback_url,
                    required_scopes=tuple(local_row.required_scopes or ()) if local_row is not None else (),
                    remote_subscription_id=_first_remote_id(owned_remote),
                    last_verified_at=now,
                    last_install_attempt_at=now,
                    error_code=exc.error_code,
                    error_message=str(exc),
                )

        for topic, local_row in local_rows.items():
            if topic in registry_topics:
                continue
            if local_row.status == ShopifyWebhookSubscriptionStatusEnum.REMOVED:
                continue
            if topic in backend_remote_by_topic:
                continue
            await _upsert_local_subscription_row(
                ctx,
                local_row=local_row,
                integration=integration,
                topic=topic,
                callback_url=callback_url,
                required_scopes=tuple(local_row.required_scopes or ()),
                status=ShopifyWebhookSubscriptionStatusEnum.REMOVED,
                remote_subscription_id=None,
                installed_at=local_row.installed_at,
                last_verified_at=now,
                last_install_attempt_at=local_row.last_install_attempt_at,
                last_error_code=None,
                last_error_message=None,
            )
            removed_topics.append(topic)

        await create_shopify_integration_event(
            ctx.session,
            workspace_id=integration.workspace_id,
            shop_integration_id=integration.client_id,
            event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC,
            severity=(
                ShopifyIntegrationEventSeverityEnum.WARNING
                if failed_topics or missing_scope_topics
                else ShopifyIntegrationEventSeverityEnum.INFO
            ),
            message="Shopify webhook subscription sync completed.",
            metadata_json={
                "shop_domain": integration.shop_domain,
                "created_topics": created_topics,
                "removed_topics": removed_topics,
                "verified_topics": verified_topics,
                "missing_scope_topics": missing_scope_topics,
                "failed_topics": failed_topics,
            },
            created_by_id=ctx.user_id or integration.updated_by_id or integration.created_by_id,
        )

    return {
        "shop_integration_id": integration.client_id,
        "shop_domain": integration.shop_domain,
        "created_topics": created_topics,
        "removed_topics": removed_topics,
        "verified_topics": verified_topics,
        "missing_scope_topics": missing_scope_topics,
        "failed_topics": failed_topics,
    }


async def _load_shopify_integration(ctx: ServiceContext, shop_integration_id: str) -> ShopifyShopIntegration:
    integration = await ctx.session.get(ShopifyShopIntegration, shop_integration_id)
    if integration is None:
        raise ValidationError("shop_integration_id does not reference an existing Shopify integration.")
    if integration.is_deleted:
        raise ValidationError("Shopify integration is deleted.")
    if integration.status not in _SYNCABLE_INTEGRATION_STATUSES:
        raise ValidationError("Shopify integration is not in a syncable status.")
    if not integration.access_token_encrypted:
        raise ValidationError("Shopify integration does not have an access token.")
    return integration


async def _load_local_subscription_rows(
    ctx: ServiceContext,
    shop_integration_id: str,
) -> dict[str, ShopifyWebhookSubscription]:
    rows = (
        await ctx.session.execute(
            select(ShopifyWebhookSubscription).where(
                ShopifyWebhookSubscription.shop_integration_id == shop_integration_id
            )
        )
    ).scalars().all()
    return {row.topic: row for row in rows}


def _build_callback_url() -> str:
    if not settings.shopify_webhook_base_url:
        raise ValidationError("SHOPIFY_WEBHOOK_BASE_URL is not configured.")
    return f"{settings.shopify_webhook_base_url.rstrip('/')}{SHOPIFY_WEBHOOK_CALLBACK_PATH}"


def _first_remote_id(remote_subscriptions: list[RemoteWebhookSubscription]) -> str | None:
    if not remote_subscriptions:
        return None
    return remote_subscriptions[0].id


def _log_missing_scope(
    shop_domain: str,
    topic: str,
    required_scopes: tuple[str, ...],
    granted_scopes: list[str] | None,
) -> None:
    if not settings.shopify_integration_debug_logs:
        return
    granted_scope_set = set(granted_scopes or [])
    missing_scopes = sorted(scope for scope in required_scopes if scope not in granted_scope_set)
    logger.debug(
        "Shopify webhook sync missing required scopes | shop_domain=%s topic=%s missing_scopes=%s",
        shop_domain,
        topic,
        ",".join(missing_scopes),
    )


async def _mark_topic_failed(
    ctx: ServiceContext,
    *,
    local_row: ShopifyWebhookSubscription | None,
    integration: ShopifyShopIntegration,
    topic: str,
    callback_url: str,
    required_scopes: tuple[str, ...],
    remote_subscription_id: str | None,
    last_verified_at: datetime,
    last_install_attempt_at: datetime,
    error_code: str,
    error_message: str,
) -> None:
    await _upsert_local_subscription_row(
        ctx,
        local_row=local_row,
        integration=integration,
        topic=topic,
        callback_url=callback_url,
        required_scopes=required_scopes,
        status=ShopifyWebhookSubscriptionStatusEnum.FAILED,
        remote_subscription_id=remote_subscription_id,
        installed_at=local_row.installed_at if local_row is not None else None,
        last_verified_at=last_verified_at,
        last_install_attempt_at=last_install_attempt_at,
        last_error_code=error_code,
        last_error_message=error_message,
    )


async def _upsert_local_subscription_row(
    ctx: ServiceContext,
    *,
    local_row: ShopifyWebhookSubscription | None,
    integration: ShopifyShopIntegration,
    topic: str,
    callback_url: str,
    required_scopes: tuple[str, ...],
    status: ShopifyWebhookSubscriptionStatusEnum,
    remote_subscription_id: str | None,
    installed_at: datetime | None,
    last_verified_at: datetime | None,
    last_install_attempt_at: datetime | None,
    last_error_code: str | None,
    last_error_message: str | None,
) -> ShopifyWebhookSubscription:
    row = local_row
    if row is None:
        row = ShopifyWebhookSubscription(
            workspace_id=integration.workspace_id,
            shop_integration_id=integration.client_id,
            topic=topic,
            callback_url=callback_url,
        )
        ctx.session.add(row)

    row.callback_url = callback_url
    row.remote_subscription_id = remote_subscription_id
    row.payload_format = _payload_format_for_topic(topic, fallback=row.payload_format)
    row.required_scopes = list(required_scopes)
    row.status = status
    row.installed_at = installed_at
    row.last_verified_at = last_verified_at
    row.last_install_attempt_at = last_install_attempt_at
    row.last_error_code = last_error_code
    row.last_error_message = last_error_message
    await ctx.session.flush()
    return row


def _payload_format_for_topic(
    topic: str,
    *,
    fallback: ShopifyWebhookPayloadFormatEnum | None,
) -> ShopifyWebhookPayloadFormatEnum:
    for definition in SHOPIFY_WEBHOOK_REGISTRY:
        if definition.topic == topic:
            return definition.payload_format
    return fallback or ShopifyWebhookPayloadFormatEnum.JSON
