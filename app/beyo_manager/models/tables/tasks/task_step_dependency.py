from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class TaskStepDependency(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tsd"
    __tablename__ = "task_step_dependencies"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dependent_step_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("task_steps.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    prerequisite_step_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("task_steps.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index(
            "uix_task_step_dependencies_active",
            "workspace_id",
            "dependent_step_id",
            "prerequisite_step_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
        CheckConstraint(
            "dependent_step_id != prerequisite_step_id",
            name="ck_task_step_dependencies_no_self_ref",
        ),
    )
