from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsInaccurateTimeMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserDailyWorkStats(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsInaccurateTimeMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "udwr"
    __tablename__ = "user_daily_work_stats"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_display_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", "work_date",
            name="uq_user_daily_work_stats_workspace_user_date",
        ),
        Index("ix_user_daily_work_stats_user_date", "user_id", "work_date"),
    )
