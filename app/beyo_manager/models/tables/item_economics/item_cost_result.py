from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class ItemCostResult(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "icr"
    __tablename__ = "item_cost_results"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), ForeignKey("items.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(String(64), ForeignKey("item_cost_evaluations.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    actual_worker_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_worker_minutes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    consumed_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    variance_worker_minutes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    variance_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    task_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    task_state_snapshot: Mapped[TaskStateEnum] = mapped_column(SAEnum(TaskStateEnum, name="task_state_enum", create_type=False), nullable=False)
    calculation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("actual_worker_seconds >= 0", name="ck_item_cost_results_actual_worker_seconds_non_negative"),
        UniqueConstraint("task_id", name="uq_item_cost_results_task_id"),
    )
