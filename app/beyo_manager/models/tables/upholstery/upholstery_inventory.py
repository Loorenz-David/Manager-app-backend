from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import (
    UpholsteryCurrencyEnum,
    UpholsteryInventoryConditionEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UpholsteryInventory(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uin"
    __tablename__ = "upholstery_inventory"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("upholsteries.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    minimum_to_have: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_to_have: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_inventory_value_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[UpholsteryCurrencyEnum | None] = mapped_column(
        SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=True), nullable=True
    )
    planning_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inventory_condition: Mapped[UpholsteryInventoryConditionEnum] = mapped_column(
        SAEnum(
            UpholsteryInventoryConditionEnum,
            name="upholstery_inventory_condition_enum",
            create_type=True,
        ),
        nullable=False,
        default=UpholsteryInventoryConditionEnum.AVAILABLE,
        index=True,
    )
    current_stored_amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    current_amount_in_use_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    current_amount_in_need_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    current_amount_ordered_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    total_upholstery_used_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    total_upholstery_used_inventory_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    total_upholstery_used_surplus_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    total_upholstery_surplus_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    latest_projection_history_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
        UniqueConstraint("workspace_id", "upholstery_id", name="uq_upholstery_inventory_workspace_upholstery"),
        CheckConstraint("minimum_to_have IS NULL OR minimum_to_have >= 0", name="ck_upholstery_inventory_min_positive"),
        CheckConstraint("maximum_to_have IS NULL OR maximum_to_have >= 0", name="ck_upholstery_inventory_max_positive"),
        CheckConstraint(
            "maximum_to_have IS NULL OR minimum_to_have IS NULL OR maximum_to_have >= minimum_to_have",
            name="ck_upholstery_inventory_max_gte_min",
        ),
        CheckConstraint(
            "projected_inventory_value_minor IS NULL OR projected_inventory_value_minor >= 0",
            name="ck_upholstery_inventory_value_positive",
        ),
    )
