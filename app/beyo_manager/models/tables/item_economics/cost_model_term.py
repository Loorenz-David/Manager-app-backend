from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class CostModelTerm(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "cmvt"
    __tablename__ = "cost_model_terms"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    cost_model_version_id: Mapped[str] = mapped_column(String(64), ForeignKey("cost_model_versions.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    calculation_type: Mapped[CostModelTermCalculationTypeEnum] = mapped_column(SAEnum(CostModelTermCalculationTypeEnum, name="cost_model_term_calculation_type_enum", create_type=True), nullable=False)
    percent_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    fixed_amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    updated_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (
        CheckConstraint("(calculation_type = 'percentage_of_expected_sale_price' AND percent_value IS NOT NULL AND fixed_amount_minor IS NULL) OR (calculation_type = 'fixed_amount' AND percent_value IS NULL AND fixed_amount_minor IS NOT NULL) OR (calculation_type = 'item_purchase_cost' AND percent_value IS NULL AND fixed_amount_minor IS NULL)", name="ck_cost_model_terms_value_by_type"),
        CheckConstraint("percent_value IS NULL OR percent_value >= 0", name="ck_cost_model_terms_percent_value_non_negative"),
        CheckConstraint("fixed_amount_minor IS NULL OR fixed_amount_minor >= 0", name="ck_cost_model_terms_fixed_amount_minor_non_negative"),
        Index("uix_cost_model_terms_purchase_cost", "cost_model_version_id", unique=True, postgresql_where=text("calculation_type = 'item_purchase_cost' AND is_deleted = false")),
        Index("uix_cost_model_terms_name_active", "cost_model_version_id", "name", unique=True, postgresql_where=text("is_deleted = false")),
    )
