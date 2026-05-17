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

from beyo_manager.domain.items.enums import (
    ItemCurrencyEnum,
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ItemUpholsteryRequirement(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "iur"
    __tablename__ = "item_upholstery_requirements"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_upholstery_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("item_upholsteries.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_inventory_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    value_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[ItemCurrencyEnum | None] = mapped_column(
        SAEnum(ItemCurrencyEnum, name="item_currency_enum", create_type=False), nullable=True
    )
    source: Mapped[ItemUpholsteryRequirementSourceEnum] = mapped_column(
        SAEnum(
            ItemUpholsteryRequirementSourceEnum,
            name="item_upholstery_requirement_source_enum",
            create_type=True,
        ),
        nullable=False,
        index=True,
    )
    state: Mapped[ItemUpholsteryRequirementStateEnum] = mapped_column(
        SAEnum(
            ItemUpholsteryRequirementStateEnum,
            name="item_upholstery_requirement_state_enum",
            create_type=True,
        ),
        nullable=False,
        default=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    in_use_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        Index(
            "ix_item_upholstery_requirements_workspace_upholstery_state",
            "workspace_id",
            "item_upholstery_id",
            "state",
        ),
        CheckConstraint(
            "amount_meters IS NULL OR amount_meters >= 0",
            name="ck_item_upholstery_requirements_amount_positive",
        ),
        CheckConstraint(
            "value_minor IS NULL OR value_minor >= 0",
            name="ck_item_upholstery_requirements_value_positive",
        ),
    )
