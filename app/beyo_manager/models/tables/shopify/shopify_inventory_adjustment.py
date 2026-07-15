from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.shopify.enums import ShopifyInventoryAdjustmentStatusEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ShopifyInventoryAdjustment(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpia"
    __tablename__ = "shopify_inventory_adjustments"
    __table_args__ = (
        UniqueConstraint(
            "shop_integration_id",
            "frontend_client_id",
            "shopify_location_id",
            name="uq_shopify_inventory_adjustments_idempotency",
        ),
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
    sync_item_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("shopify_product_sync_items.client_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    frontend_client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    shopify_inventory_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    shopify_location_id: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ShopifyInventoryAdjustmentStatusEnum] = mapped_column(
        SAEnum(
            ShopifyInventoryAdjustmentStatusEnum,
            name="shopify_inventory_adjustment_status_enum",
            create_type=True,
        ),
        nullable=False,
        default=ShopifyInventoryAdjustmentStatusEnum.PENDING,
        server_default=ShopifyInventoryAdjustmentStatusEnum.PENDING.value,
        index=True,
    )
    reference_uri: Mapped[str] = mapped_column(String(255), nullable=False)
    shopify_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
