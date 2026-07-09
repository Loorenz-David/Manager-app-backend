from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ShopifyIntegrationEvent(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpevt"
    __tablename__ = "shopify_integration_events"
    __table_args__ = (
        Index("ix_shopify_integration_events_workspace_shop_integration", "workspace_id", "shop_integration_id"),
        Index("ix_shopify_integration_events_event_type", "event_type"),
        Index("ix_shopify_integration_events_severity", "severity"),
        Index("ix_shopify_integration_events_created_at", "created_at"),
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
    event_type: Mapped[ShopifyIntegrationEventTypeEnum] = mapped_column(
        SAEnum(ShopifyIntegrationEventTypeEnum, name="shopify_integration_event_type_enum", create_type=True),
        nullable=False,
        index=True,
    )
    severity: Mapped[ShopifyIntegrationEventSeverityEnum] = mapped_column(
        SAEnum(
            ShopifyIntegrationEventSeverityEnum,
            name="shopify_integration_event_severity_enum",
            create_type=True,
        ),
        nullable=False,
        default=ShopifyIntegrationEventSeverityEnum.INFO,
        server_default=ShopifyIntegrationEventSeverityEnum.INFO.value,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
