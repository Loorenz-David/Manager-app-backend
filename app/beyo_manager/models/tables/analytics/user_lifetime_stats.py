from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserLifetimeStats(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "usr_stat"
    __tablename__ = "user_lifetime_stats"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_display_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_user_lifetime_stats_workspace_user"),
    )
