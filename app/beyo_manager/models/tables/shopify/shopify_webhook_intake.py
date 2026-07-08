from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.shopify.enums import ShopifyWebhookIntakeStatusEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ShopifyWebhookIntake(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpwhi"
    __tablename__ = "shopify_webhook_intakes"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_shopify_webhook_intakes_dedupe_key"),
        Index("ix_shopify_webhook_intakes_workspace_status", "workspace_id", "status"),
        Index("ix_shopify_webhook_intakes_shop_integration_topic", "shop_integration_id", "topic"),
        Index("ix_shopify_webhook_intakes_received_at", "received_at"),
        Index("ix_shopify_webhook_intakes_webhook_id", "webhook_id"),
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
    shop_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    webhook_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_payload: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[ShopifyWebhookIntakeStatusEnum] = mapped_column(
        SAEnum(ShopifyWebhookIntakeStatusEnum, name="shopify_webhook_intake_status_enum", create_type=True),
        nullable=False,
        default=ShopifyWebhookIntakeStatusEnum.RECEIVED,
        server_default=ShopifyWebhookIntakeStatusEnum.RECEIVED.value,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
