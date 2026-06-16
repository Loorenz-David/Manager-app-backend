from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UpholsterySupplierLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "usl"
    __tablename__ = "upholstery_supplier_links"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("upholsteries.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supplier_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("suppliers.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    priority_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[UpholsteryCurrencyEnum | None] = mapped_column(
        SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=False), nullable=True
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        UniqueConstraint(
            "workspace_id",
            "upholstery_id",
            "supplier_id",
            name="uq_upholstery_supplier_links_workspace_upholstery_supplier",
        ),
        CheckConstraint(
            "price_minor IS NULL OR price_minor >= 0",
            name="ck_upholstery_supplier_links_price_positive",
        ),
        CheckConstraint(
            "priority_order IS NULL OR priority_order >= 0",
            name="ck_upholstery_supplier_links_priority_positive",
        ),
        Index(
            "ix_upholstery_supplier_links_workspace_upholstery_preferred",
            "workspace_id",
            "upholstery_id",
            "preferred",
        ),
    )
