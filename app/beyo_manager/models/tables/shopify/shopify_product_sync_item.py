from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.shopify.enums import ShopifyProductSyncItemStatusEnum, ShopifyProductSyncOperationEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ShopifyProductSyncItem(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpsi"
    __tablename__ = "shopify_product_sync_items"
    __table_args__ = (
        Index("ix_shopify_product_sync_items_workspace_status", "workspace_id", "status"),
        Index("ix_shopify_product_sync_items_shop_integration_status", "shop_integration_id", "status"),
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
    frontend_client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_operation: Mapped[ShopifyProductSyncOperationEnum | None] = mapped_column(
        SAEnum(
            ShopifyProductSyncOperationEnum,
            name="shopify_product_sync_operation_enum",
            create_type=True,
        ),
        nullable=True,
    )
    status: Mapped[ShopifyProductSyncItemStatusEnum] = mapped_column(
        SAEnum(
            ShopifyProductSyncItemStatusEnum,
            name="shopify_product_sync_item_status_enum",
            create_type=True,
        ),
        nullable=False,
        default=ShopifyProductSyncItemStatusEnum.PENDING,
        server_default=ShopifyProductSyncItemStatusEnum.PENDING.value,
        index=True,
    )
    normalized_payload_json: Mapped[dict] = mapped_column("normalized_payload", JSONB, nullable=False)
    shopify_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shopify_variant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
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
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
