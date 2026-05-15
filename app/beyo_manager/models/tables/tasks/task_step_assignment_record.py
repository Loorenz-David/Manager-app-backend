from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class TaskStepAssignmentRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tsar"
    __tablename__ = "task_step_assignment_records"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("task_steps.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_worker_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        Index(
            "ix_task_step_assignment_records_workspace_step_assigned",
            "workspace_id",
            "step_id",
            "assigned_at",
        ),
        Index(
            "uix_task_step_assignment_records_active",
            "workspace_id",
            "step_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )
