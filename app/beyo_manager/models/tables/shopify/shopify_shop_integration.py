from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)

_ACTIVE_SHOPIFY_INTEGRATION_STATUSES = (
    "'pending_install', 'active', 'needs_reauth', 'scopes_outdated', 'webhooks_outdated', 'error'"
)


class ShopifyShopIntegration(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpint"
    __tablename__ = "shopify_shop_integrations"
    __table_args__ = (
        Index("ix_shopify_shop_integrations_workspace_status", "workspace_id", "status"),
        Index("ix_shopify_shop_integrations_shop_domain_status", "shop_domain", "status"),
        Index("ix_shopify_shop_integrations_created_at", "created_at"),
        Index("ix_shopify_shop_integrations_is_deleted", "is_deleted"),
        Index(
            "uix_shopify_shop_integrations_shop_domain_active",
            "shop_domain",
            unique=True,
            postgresql_where=text(
                f"is_deleted = false AND status IN ({_ACTIVE_SHOPIFY_INTEGRATION_STATUSES})"
            ),
        ),
        Index(
            "uix_shopify_shop_integrations_workspace_shop_domain_active",
            "workspace_id",
            "shop_domain",
            unique=True,
            postgresql_where=text(
                f"is_deleted = false AND status IN ({_ACTIVE_SHOPIFY_INTEGRATION_STATUSES})"
            ),
        ),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shop_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="shopify", server_default="shopify")
    status: Mapped[ShopifyIntegrationStatusEnum] = mapped_column(
        SAEnum(ShopifyIntegrationStatusEnum, name="shopify_integration_status_enum", create_type=True),
        nullable=False,
        default=ShopifyIntegrationStatusEnum.PENDING_INSTALL,
        server_default=ShopifyIntegrationStatusEnum.PENDING_INSTALL.value,
        index=True,
    )
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_scopes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    requested_scopes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    api_version: Mapped[str] = mapped_column(String(32), nullable=False)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uninstalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_check_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
