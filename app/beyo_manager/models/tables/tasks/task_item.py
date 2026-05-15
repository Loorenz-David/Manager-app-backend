from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class TaskItem(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tim"
    __tablename__ = "task_items"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("items.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    role: Mapped[TaskItemRoleEnum] = mapped_column(
        SAEnum(TaskItemRoleEnum, name="task_item_role_enum", create_type=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_task_items_workspace_item", "workspace_id", "item_id"),
        Index(
            "uix_task_items_active",
            "workspace_id",
            "task_id",
            "item_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
        Index(
            "uix_task_items_primary_active",
            "workspace_id",
            "task_id",
            unique=True,
            postgresql_where=text("role = 'primary' AND removed_at IS NULL"),
        ),
    )
