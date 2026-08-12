from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.tasks.enums import TaskReturnSourceEnum, TaskTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class ItemCostEvaluation(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ice"
    __tablename__ = "item_cost_evaluations"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), ForeignKey("items.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    kind: Mapped[ItemCostEvaluationKindEnum] = mapped_column(SAEnum(ItemCostEvaluationKindEnum, name="item_cost_evaluation_kind_enum", create_type=True), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_type_snapshot: Mapped[TaskTypeEnum] = mapped_column(SAEnum(TaskTypeEnum, name="business_task_type_enum", create_type=False), nullable=False)
    return_source_snapshot: Mapped[TaskReturnSourceEnum | None] = mapped_column(SAEnum(TaskReturnSourceEnum, name="task_return_source_enum", create_type=False), nullable=True)
    expected_sale_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_cost_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[ItemCurrencyEnum] = mapped_column(SAEnum(ItemCurrencyEnum, name="item_valuation_currency_enum", create_type=False), nullable=False)
    cost_model_version_id: Mapped[str] = mapped_column(String(64), ForeignKey("cost_model_versions.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    production_cost_group_id: Mapped[str] = mapped_column(String(64), ForeignKey("production_cost_groups.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    production_cost_basis_version_id: Mapped[str] = mapped_column(String(64), ForeignKey("production_cost_basis_versions.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    monthly_paid_hours_snapshot: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    planning_utilization_percent_snapshot: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fixed_monthly_cost_minor_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_per_worker_minute_minor_snapshot: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    production_budget_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_worker_minutes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    calculation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("item_cost_evaluations.client_id", use_alter=True, name="fk_item_cost_evaluations_superseded_by_id", ondelete="RESTRICT"), nullable=True, index=True)
    promoted_from_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("item_cost_evaluations.client_id", use_alter=True, name="fk_item_cost_evaluations_promoted_from_id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    updated_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (
        CheckConstraint("expected_sale_price_minor >= 0", name="ck_ice_expected_sale_price_minor_non_negative"),
        CheckConstraint("purchase_cost_minor IS NULL OR purchase_cost_minor >= 0", name="ck_ice_purchase_cost_minor_non_negative"),
        Index("uix_item_cost_evaluations_current", "task_id", unique=True, postgresql_where=text("kind = 'committed' AND superseded_at IS NULL AND is_deleted = false")),
    )
