from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum, UpholsteryOrderStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UpholsteryOrder(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uor"
    __tablename__ = "upholstery_orders"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_inventory_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("upholstery_inventory.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    upholstery_supplier_link_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("upholstery_supplier_links.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    supplier_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("suppliers.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    order_amount_meters: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    price_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[UpholsteryCurrencyEnum | None] = mapped_column(
        SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=False), nullable=True
    )
    order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=True),
        nullable=False,
        default=UpholsteryOrderStateEnum.DRAFT,
    )
    ordered_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    expected_receive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
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
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_upholstery_orders_workspace_state_created", "workspace_id", "state", "created_at"),
        CheckConstraint(
            "order_amount_meters >= 0",
            name="ck_upholstery_orders_amount_positive",
        ),
        CheckConstraint(
            "price_minor IS NULL OR price_minor >= 0",
            name="ck_upholstery_orders_price_positive",
        ),
    )
