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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.task_steps.enums import (
    StepEventReasonEnum,
    StepStateRecordAccuracyMeasuredByEnum,
    TaskStepStateEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class StepStateRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ssr"
    __tablename__ = "step_state_records"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("task_steps.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[TaskStepStateEnum] = mapped_column(
        SAEnum(TaskStepStateEnum, name="task_step_state_enum", create_type=False), nullable=False, index=True
    )
    reason: Mapped[StepEventReasonEnum | None] = mapped_column(
        SAEnum(StepEventReasonEnum, name="step_event_reason_enum", create_type=True), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    accuracy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy_measured_by: Mapped[StepStateRecordAccuracyMeasuredByEnum | None] = mapped_column(
        SAEnum(
            StepStateRecordAccuracyMeasuredByEnum,
            name="step_state_record_accuracy_measured_by_enum",
            create_type=True,
        ),
        nullable=True,
    )
    taken_from_average: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recorded_time_marked_wrong: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_step_state_records_workspace_step_entered", "workspace_id", "step_id", "entered_at"),
        Index(
            "uix_step_state_records_active",
            "workspace_id",
            "step_id",
            unique=True,
            postgresql_where=text("exited_at IS NULL"),
        ),
        CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 100)",
            name="ck_step_state_records_accuracy_range",
        ),
        CheckConstraint(
            "exited_at IS NULL OR exited_at >= entered_at",
            name="ck_step_state_records_exited_after_entered",
        ),
    )
