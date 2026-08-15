from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class ProductionCostBasisVersion(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "pcbv"
    __tablename__ = "production_cost_basis_versions"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    production_cost_group_id: Mapped[str] = mapped_column(String(64), ForeignKey("production_cost_groups.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    fixed_monthly_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[ItemCurrencyEnum] = mapped_column(SAEnum(ItemCurrencyEnum, name="production_cost_basis_version_currency_enum", create_type=True), nullable=False)
    monthly_paid_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    planning_utilization_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    cost_per_worker_minute_minor: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    updated_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (
        CheckConstraint("fixed_monthly_cost_minor > 0", name="ck_pcbv_fixed_monthly_cost_minor_positive"),
        CheckConstraint("cost_per_worker_minute_minor > 0", name="ck_pcbv_cost_per_worker_minute_minor_positive"),
        CheckConstraint("monthly_paid_hours > 0", name="ck_pcbv_monthly_paid_hours_positive"),
        CheckConstraint("planning_utilization_percent > 0", name="ck_pcbv_planning_utilization_percent_positive"),
        CheckConstraint("planning_utilization_percent <= 100", name="ck_pcbv_planning_utilization_percent_max"),
        CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from", name="ck_production_cost_basis_versions_effective_window"),
        Index("uix_production_cost_basis_versions_open", "production_cost_group_id", unique=True, postgresql_where=text("effective_to IS NULL AND is_deleted = false")),
    )
