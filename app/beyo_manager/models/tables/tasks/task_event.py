from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import (
    TaskDomainEventLifecycleStateEnum,
    TaskEventErrorCodeEnum,
    TaskEventTypeEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class TaskEvent(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tev"
    __tablename__ = "task_events"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_type: Mapped[TaskEventTypeEnum] = mapped_column(
        SAEnum(TaskEventTypeEnum, name="task_event_type_enum", create_type=True), nullable=False, index=True
    )
    event_lifecycle_state: Mapped[TaskDomainEventLifecycleStateEnum] = mapped_column(
        SAEnum(
            TaskDomainEventLifecycleStateEnum,
            name="task_domain_event_lifecycle_state_enum",
            create_type=True,
        ),
        nullable=False,
        default=TaskDomainEventLifecycleStateEnum.RECORDED,
        index=True,
    )
    error_code: Mapped[TaskEventErrorCodeEnum | None] = mapped_column(
        SAEnum(TaskEventErrorCodeEnum, name="task_event_error_code_enum", create_type=True),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
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

    __table_args__ = (Index("ix_task_events_workspace_task_occurred", "workspace_id", "task_id", "occurred_at"),)
