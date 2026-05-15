from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import (
    InventoryWarningTierEnum,
    SourcingEscalationPolicyEnum,
    ThresholdPolicyScopeEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UpholsteryInventoryThresholdPolicy(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "utp"
    __tablename__ = "upholstery_inventory_threshold_policies"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scope: Mapped[ThresholdPolicyScopeEnum] = mapped_column(
        SAEnum(ThresholdPolicyScopeEnum, name="threshold_policy_scope_enum", create_type=True),
        nullable=False,
        index=True,
    )
    upholstery_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("upholsteries.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    low_stock_minimum_meters: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    low_stock_ratio: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    out_of_stock_epsilon_meters: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    escalation_policy: Mapped[SourcingEscalationPolicyEnum | None] = mapped_column(
        SAEnum(
            SourcingEscalationPolicyEnum,
            name="sourcing_escalation_policy_enum",
            create_type=True,
        ),
        nullable=True,
    )
    warning_tier: Mapped[InventoryWarningTierEnum | None] = mapped_column(
        SAEnum(InventoryWarningTierEnum, name="inventory_warning_tier_enum", create_type=True),
        nullable=True,
    )
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
            "scope",
            "upholstery_id",
            "effective_from",
            name="uq_upholstery_inv_threshold_policies_unique",
        ),
        CheckConstraint(
            "low_stock_minimum_meters IS NULL OR low_stock_minimum_meters >= 0",
            name="ck_utp_low_stock_min_positive",
        ),
        CheckConstraint(
            "low_stock_ratio IS NULL OR (low_stock_ratio >= 0 AND low_stock_ratio <= 1)",
            name="ck_utp_low_stock_ratio_range",
        ),
        CheckConstraint(
            "out_of_stock_epsilon_meters IS NULL OR out_of_stock_epsilon_meters >= 0",
            name="ck_utp_epsilon_positive",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_utp_effective_window",
        ),
        CheckConstraint(
            "scope != 'upholstery' OR upholstery_id IS NOT NULL",
            name="ck_utp_upholstery_scope_requires_id",
        ),
    )
