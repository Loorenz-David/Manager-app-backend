from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.errors.external_service import ShopifyGraphQLError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop import (
    _SYNCABLE_INTEGRATION_STATUSES,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.webhook_subscription_client import (
    delete_remote_webhook_subscription,
    list_remote_webhook_subscriptions,
)
from beyo_manager.domain.shopify.webhook_registry import SHOPIFY_WEBHOOK_CALLBACK_PATH


class RemoveShopifyWebhooksForShopRequest(BaseModel):
    shop_integration_id: str

    @field_validator("shop_integration_id")
    @classmethod
    def _required_string_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank.")
        return value


def parse_remove_shopify_webhooks_for_shop_request(data: dict) -> RemoveShopifyWebhooksForShopRequest:
    try:
        return RemoveShopifyWebhooksForShopRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def remove_shopify_webhooks_for_shop(ctx: ServiceContext) -> dict:
    request = parse_remove_shopify_webhooks_for_shop_request(ctx.incoming_data)
    integration = await ctx.session.get(ShopifyShopIntegration, request.shop_integration_id)
    if integration is None:
        raise ValidationError("shop_integration_id does not reference an existing Shopify integration.")
    if integration.is_deleted:
        raise ValidationError("Shopify integration is deleted.")
    if integration.status not in _SYNCABLE_INTEGRATION_STATUSES:
        raise ValidationError("Shopify integration is not in a removable status.")
    if not integration.access_token_encrypted:
        raise ValidationError("Shopify integration does not have an access token.")

    callback_url = _build_callback_url()
    now = datetime.now(timezone.utc)
    remote_subscriptions = await list_remote_webhook_subscriptions(
        shop_domain=integration.shop_domain,
        access_token_encrypted=integration.access_token_encrypted,
    )
    owned_remote_subscriptions = [
        remote_subscription
        for remote_subscription in remote_subscriptions
        if remote_subscription.callback_url == callback_url
    ]
    local_rows = (
        await ctx.session.execute(
            select(ShopifyWebhookSubscription).where(
                ShopifyWebhookSubscription.shop_integration_id == integration.client_id
            )
        )
    ).scalars().all()
    local_rows_by_topic = {row.topic: row for row in local_rows}

    removed_topics: list[str] = []
    failed_topics: list[str] = []

    async with maybe_begin(ctx.session):
        per_topic_failures: set[str] = set()
        for remote_subscription in owned_remote_subscriptions:
            try:
                await delete_remote_webhook_subscription(
                    shop_domain=integration.shop_domain,
                    access_token_encrypted=integration.access_token_encrypted,
                    remote_subscription_id=remote_subscription.id,
                )
            except ShopifyGraphQLError as exc:
                per_topic_failures.add(remote_subscription.topic)
                failed_topics.append(remote_subscription.topic)
                row = local_rows_by_topic.get(remote_subscription.topic)
                if row is not None:
                    row.status = ShopifyWebhookSubscriptionStatusEnum.FAILED
                    row.last_verified_at = now
                    row.last_install_attempt_at = now
                    row.last_error_code = exc.error_code
                    row.last_error_message = str(exc)
                    await ctx.session.flush()
                continue

            if remote_subscription.topic not in local_rows_by_topic:
                removed_topics.append(remote_subscription.topic)

        for row in local_rows:
            if row.topic in per_topic_failures:
                continue
            row.status = ShopifyWebhookSubscriptionStatusEnum.REMOVED
            row.remote_subscription_id = None
            row.last_verified_at = now
            row.last_error_code = None
            row.last_error_message = None
            removed_topics.append(row.topic)
        await ctx.session.flush()

        await create_shopify_integration_event(
            ctx.session,
            workspace_id=integration.workspace_id,
            shop_integration_id=integration.client_id,
            event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC,
            severity=(
                ShopifyIntegrationEventSeverityEnum.WARNING
                if failed_topics
                else ShopifyIntegrationEventSeverityEnum.INFO
            ),
            message="Shopify webhook removal completed.",
            metadata_json={
                "shop_domain": integration.shop_domain,
                "removed_topics": sorted(set(removed_topics)),
                "failed_topics": failed_topics,
            },
            created_by_id=ctx.user_id or integration.updated_by_id or integration.created_by_id,
        )

    return {
        "shop_integration_id": integration.client_id,
        "shop_domain": integration.shop_domain,
        "removed_topics": sorted(set(removed_topics)),
        "failed_topics": failed_topics,
    }


def _build_callback_url() -> str:
    if not settings.shopify_webhook_base_url:
        raise ValidationError("SHOPIFY_WEBHOOK_BASE_URL is not configured.")
    return f"{settings.shopify_webhook_base_url.rstrip('/')}{SHOPIFY_WEBHOOK_CALLBACK_PATH}"
