from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class AggregateMetricsTimeMixin:
    total_working_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pause_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_ended_shift_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AggregateMetricsCountsMixin:
    total_working_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pause_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_ended_shift_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_completed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class AggregateMetricsTotalsMixin:
    total_issues_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_issues_resolved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AggregateMetricsCostMixin:
    total_cost_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
