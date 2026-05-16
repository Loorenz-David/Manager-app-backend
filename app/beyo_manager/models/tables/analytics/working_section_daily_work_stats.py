from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkingSectionDailyWorkStats(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "wsdws"
    __tablename__ = "working_section_daily_work_stats"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    section_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "working_section_id", "work_date",
            name="uq_working_section_daily_work_stats_workspace_section_date",
        ),
        Index("ix_working_section_daily_work_stats_section_date", "working_section_id", "work_date"),
    )
