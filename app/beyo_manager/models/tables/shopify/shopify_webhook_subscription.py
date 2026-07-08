from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.shopify.enums import (
    ShopifyWebhookPayloadFormatEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ShopifyWebhookSubscription(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpwhs"
    __tablename__ = "shopify_webhook_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "shop_integration_id",
            "topic",
            name="uq_shopify_webhook_subscriptions_shop_integration_topic",
        ),
        Index("ix_shopify_webhook_subscriptions_workspace_shop_integration", "workspace_id", "shop_integration_id"),
        Index("ix_shopify_webhook_subscriptions_topic_status", "topic", "status"),
        Index("ix_shopify_webhook_subscriptions_remote_subscription_id", "remote_subscription_id"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shop_integration_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("shopify_shop_integrations.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    callback_url: Mapped[str] = mapped_column(Text, nullable=False)
    remote_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_format: Mapped[ShopifyWebhookPayloadFormatEnum] = mapped_column(
        SAEnum(
            ShopifyWebhookPayloadFormatEnum,
            name="shopify_webhook_payload_format_enum",
            create_type=True,
        ),
        nullable=False,
        default=ShopifyWebhookPayloadFormatEnum.JSON,
        server_default=ShopifyWebhookPayloadFormatEnum.JSON.value,
    )
    required_scopes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[ShopifyWebhookSubscriptionStatusEnum] = mapped_column(
        SAEnum(
            ShopifyWebhookSubscriptionStatusEnum,
            name="shopify_webhook_subscription_status_enum",
            create_type=True,
        ),
        nullable=False,
        default=ShopifyWebhookSubscriptionStatusEnum.PENDING,
        server_default=ShopifyWebhookSubscriptionStatusEnum.PENDING.value,
        index=True,
    )
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_install_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
