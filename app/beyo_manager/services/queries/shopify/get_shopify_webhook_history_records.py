from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import load_only, selectinload

from beyo_manager.domain.shopify.enums import ShopifyIntegrationEventTypeEnum
from beyo_manager.domain.shopify.serializers import (
    serialize_shopify_integration_event_history_record,
    serialize_shopify_webhook_intake_history_record,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext

DEFAULT_WEBHOOK_HISTORY_LIMIT = 10
MAX_WEBHOOK_HISTORY_LIMIT = 200
MIN_WEBHOOK_HISTORY_LIMIT = 1

WEBHOOK_HISTORY_EVENT_TYPES = {
    ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC,
    ShopifyIntegrationEventTypeEnum.WEBHOOK_RECEIVED,
    ShopifyIntegrationEventTypeEnum.WEBHOOK_PROCESSED,
    ShopifyIntegrationEventTypeEnum.DISCONNECT,
}


def _parse_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def get_shopify_webhook_history_records(ctx: ServiceContext) -> dict:
    shop_integration_id = str(ctx.incoming_data.get("shop_integration_id") or "").strip()
    limit = _parse_int(ctx.query_params.get("limit"), DEFAULT_WEBHOOK_HISTORY_LIMIT)
    limit = max(MIN_WEBHOOK_HISTORY_LIMIT, min(limit, MAX_WEBHOOK_HISTORY_LIMIT))
    offset = max(0, _parse_int(ctx.query_params.get("offset"), 0))

    if not shop_integration_id:
        raise NotFound("Shopify shop integration not found.")

    integration_result = await ctx.session.execute(
        select(ShopifyShopIntegration.client_id).where(
            ShopifyShopIntegration.workspace_id == ctx.workspace_id,
            ShopifyShopIntegration.client_id == shop_integration_id,
            ShopifyShopIntegration.is_deleted.is_(False),
        )
    )
    if integration_result.scalar_one_or_none() is None:
        raise NotFound("Shopify shop integration not found.")

    intake_rows = (
        await ctx.session.execute(
            select(ShopifyWebhookIntake).where(
                ShopifyWebhookIntake.workspace_id == ctx.workspace_id,
                ShopifyWebhookIntake.shop_integration_id == shop_integration_id,
            )
        )
    ).scalars().all()

    event_rows = (
        await ctx.session.execute(
            select(ShopifyIntegrationEvent)
            .options(
                selectinload(ShopifyIntegrationEvent.created_by).load_only(User.client_id, User.username, User.profile_picture)
            )
            .where(
                ShopifyIntegrationEvent.workspace_id == ctx.workspace_id,
                ShopifyIntegrationEvent.shop_integration_id == shop_integration_id,
                ShopifyIntegrationEvent.event_type.in_(WEBHOOK_HISTORY_EVENT_TYPES),
            )
        )
    ).scalars().all()

    raw_records: list[tuple] = []
    for row in intake_rows:
        raw_records.append((row.received_at, "webhook_intake", row))
    for row in event_rows:
        raw_records.append((row.created_at, "integration_event", row))

    raw_records.sort(key=lambda item: (item[0], item[2].client_id), reverse=True)
    paged = raw_records[offset : offset + limit + 1]
    has_more = len(paged) > limit
    paged = paged[:limit]

    records: list[dict] = []
    for _timestamp, record_type, row in paged:
        if record_type == "webhook_intake":
            records.append(asdict(serialize_shopify_webhook_intake_history_record(row)))
        else:
            records.append(asdict(serialize_shopify_integration_event_history_record(row)))

    return {
        "webhook_history_records": records,
        "webhook_history_records_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }