from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class TaskStep(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "tsp"
    __tablename__ = "task_steps"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[TaskStepStateEnum] = mapped_column(
        SAEnum(TaskStepStateEnum, name="task_step_state_enum", create_type=True),
        nullable=False,
        default=TaskStepStateEnum.PENDING,
        index=True,
    )
    readiness_status: Mapped[TaskStepReadinessStatusEnum] = mapped_column(
        SAEnum(TaskStepReadinessStatusEnum, name="task_step_readiness_status_enum", create_type=True),
        nullable=False,
        default=TaskStepReadinessStatusEnum.READY,
        index=True,
    )
    sequence_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_worker_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    total_dependencies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_dependencies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_time_marked_wrong: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    taken_from_average: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    working_section_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_worker_display_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    latest_state_record_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "step_state_records.client_id",
            use_alter=True,
            name="fk_task_steps_latest_state_record_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    latest_state_record: Mapped["StepStateRecord | None"] = relationship(
        "StepStateRecord",
        foreign_keys=[latest_state_record_id],
        uselist=False,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_task_steps_workspace_task_state", "workspace_id", "task_id", "state"),
        CheckConstraint("completed_dependencies >= 0", name="ck_task_steps_completed_deps_positive"),
        CheckConstraint("total_dependencies >= 0", name="ck_task_steps_total_deps_positive"),
        CheckConstraint(
            "completed_dependencies <= total_dependencies",
            name="ck_task_steps_completed_lte_total",
        ),
        CheckConstraint("total_pause_count >= 0", name="ck_task_steps_pause_count_positive"),
        CheckConstraint("total_ended_shift_count >= 0", name="ck_task_steps_ended_shift_count_positive"),
        CheckConstraint("total_pause_seconds >= 0", name="ck_task_steps_pause_seconds_positive"),
        CheckConstraint(
            "total_ended_shift_seconds >= 0",
            name="ck_task_steps_ended_shift_seconds_positive",
        ),
    )
