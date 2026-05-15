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

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ItemUpholstery(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "iup"
    __tablename__ = "item_upholsteries"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("items.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("upholsteries.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    source: Mapped[ItemUpholsterySourceEnum] = mapped_column(
        SAEnum(ItemUpholsterySourceEnum, name="item_upholstery_source_enum", create_type=True),
        nullable=False,
        index=True,
    )
    time_to_fix_in_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_requirement_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "item_upholstery_requirements.client_id",
            use_alter=True,
            name="fk_item_upholsteries_active_requirement_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
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
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_item_upholsteries_workspace_item", "workspace_id", "item_id"),
        CheckConstraint("amount_meters IS NULL OR amount_meters >= 0", name="ck_item_upholsteries_amount_positive"),
        CheckConstraint(
            "time_to_fix_in_seconds IS NULL OR time_to_fix_in_seconds >= 0",
            name="ck_item_upholsteries_time_positive",
        ),
    )
