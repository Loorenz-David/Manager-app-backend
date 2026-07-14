from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class ShopifyMetafieldPreference(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpmfp"
    __tablename__ = "shopify_metafield_preferences"
    __table_args__ = (
        Index(
            "ix_shopify_metafield_preferences_workspace_shop_category",
            "workspace_id",
            "shop_integration_id",
            "item_category_id",
        ),
        Index(
            "ix_shopify_metafield_preferences_ws_shop_category_creator",
            "workspace_id",
            "shop_integration_id",
            "item_category_id",
            "created_by_id",
        ),
        Index(
            "uix_shopify_metafield_preferences_active_scope",
            "workspace_id",
            "shop_integration_id",
            "item_category_id",
            "shopify_metafield_definition_id",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_category_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("item_categories.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shop_integration_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("shopify_shop_integrations.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    shopify_metafield_definition_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
