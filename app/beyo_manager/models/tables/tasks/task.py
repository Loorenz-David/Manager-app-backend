from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import (
    TaskFulfillmentMethodEnum,
    TaskItemLocationEnum,
    TaskPriorityEnum,
    TaskReturnMethodEnum,
    TaskReturnSourceEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class Task(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tsk"
    __tablename__ = "tasks"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_scalar_id: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[TaskTypeEnum] = mapped_column(
        SAEnum(TaskTypeEnum, name="business_task_type_enum", create_type=True), nullable=False, index=True
    )
    priority: Mapped[TaskPriorityEnum] = mapped_column(
        SAEnum(TaskPriorityEnum, name="task_priority_enum", create_type=True),
        nullable=False,
        default=TaskPriorityEnum.NORMAL,
        index=True,
    )
    state: Mapped[TaskStateEnum] = mapped_column(
        SAEnum(TaskStateEnum, name="task_state_enum", create_type=True),
        nullable=False,
        default=TaskStateEnum.PENDING,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    return_source: Mapped[TaskReturnSourceEnum | None] = mapped_column(
        SAEnum(TaskReturnSourceEnum, name="task_return_source_enum", create_type=True), nullable=True
    )
    item_location: Mapped[TaskItemLocationEnum | None] = mapped_column(
        SAEnum(TaskItemLocationEnum, name="task_item_location_enum", create_type=True), nullable=True
    )
    additional_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ready_by_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    return_method: Mapped[TaskReturnMethodEnum | None] = mapped_column(
        SAEnum(TaskReturnMethodEnum, name="task_return_method_enum", create_type=True), nullable=True
    )
    fulfillment_method: Mapped[TaskFulfillmentMethodEnum | None] = mapped_column(
        SAEnum(TaskFulfillmentMethodEnum, name="task_fulfillment_method_enum", create_type=True), nullable=True
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("customers.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    primary_phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secondary_phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secondary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_history_record_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "task_history_records.client_id",
            use_alter=True,
            name="fk_tasks_latest_history_record_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    latest_event_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "task_events.client_id",
            use_alter=True,
            name="fk_tasks_latest_event_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    recorded_time_marked_wrong: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    taken_from_average: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "task_scalar_id", name="uq_tasks_workspace_scalar_id"),
        Index("ix_tasks_workspace_state_scheduled_start", "workspace_id", "state", "scheduled_start_at"),
        CheckConstraint(
            "scheduled_end_at IS NULL OR scheduled_start_at IS NULL OR scheduled_end_at >= scheduled_start_at",
            name="ck_tasks_scheduled_end_after_start",
        ),
    )
