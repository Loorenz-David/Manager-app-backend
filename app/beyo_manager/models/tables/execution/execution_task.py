from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ExecutionTask(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "task"
    __tablename__ = "execution_tasks"

    task_type: Mapped[TaskType] = mapped_column(
        SAEnum(TaskType, name="task_type_enum", create_type=True),
        nullable=False,
        index=True,
    )
    state: Mapped[ExecutionTaskStateEnum] = mapped_column(
        SAEnum(ExecutionTaskStateEnum, name="execution_task_state_enum", create_type=True),
        nullable=False,
        default=ExecutionTaskStateEnum.OPEN,
        index=True,
    )

    try_count:  Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    max_try:    Mapped[int]        = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    worker_id:  Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    payload: Mapped["ExecutionPayload"] = relationship(
        "ExecutionPayload", back_populates="execution_task", uselist=False
    )
