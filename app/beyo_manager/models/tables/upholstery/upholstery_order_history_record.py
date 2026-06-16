from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum, UpholsteryOrderStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UpholsteryOrderHistoryRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uoh"
    __tablename__ = "upholstery_order_history_records"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("upholstery_orders.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=False),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snapshot_price_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_currency: Mapped[UpholsteryCurrencyEnum | None] = mapped_column(
        SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=False), nullable=True
    )
    snapshot_order_amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_upholstery_order_history_records_workspace_order_changed",
            "workspace_id",
            "upholstery_order_id",
            "changed_at",
        ),
        CheckConstraint(
            "snapshot_order_amount_meters IS NULL OR snapshot_order_amount_meters >= 0",
            name="ck_upholstery_order_history_records_snapshot_amount_positive",
        ),
    )
