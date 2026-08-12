from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class ItemCostEvaluationTerm(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "icet"
    __tablename__ = "item_cost_evaluation_terms"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(String(64), ForeignKey("item_cost_evaluations.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    calculation_type: Mapped[CostModelTermCalculationTypeEnum] = mapped_column(SAEnum(CostModelTermCalculationTypeEnum, name="cost_model_term_calculation_type_enum", create_type=False), nullable=False)
    percent_value: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    fixed_amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
