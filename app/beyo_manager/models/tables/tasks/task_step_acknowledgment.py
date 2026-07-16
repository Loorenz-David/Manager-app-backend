from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class TaskStepAcknowledgment(IdentityMixin, Base):
    """A per-worker read receipt for a step that appeared on a task the worker
    had already finished.

    Created when ``add_task_steps`` reopens a ``READY`` task (a reassignment):
    the newly added, worker-assigned steps each get one obligation row that the
    worker must first see (``first_seen_at``) and then acknowledge
    (``acknowledged_at``). ``reason`` snapshots the free-text note the manager
    sent with the reassignment; the frontend truncates it via the notes system.
    """

    CLIENT_ID_PREFIX = "tsa"
    __tablename__ = "task_step_acknowledgments"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("task_steps.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Denormalized so "pending reassignments on this task" is one index hit,
    # mirroring the snapshot columns already carried on TaskStep.
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # The worker who owes the acknowledgment — step.assigned_worker_id at the
    # moment of reassignment.
    worker_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Free-text note the manager attached to the reassignment. Snapshotted per
    # ack row so it stays stable even if the source note changes.
    reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Two-phase, both nullable. NULL = not yet. Timestamps instead of booleans
    # give the audit trail (when seen / when acknowledged) for free.
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        # One acknowledgment obligation per step per worker.
        Index(
            "uix_task_step_ack_step_worker",
            "workspace_id",
            "step_id",
            "worker_id",
            unique=True,
        ),
        # Hot query: a worker's pending acknowledgments. Partial index keeps it
        # tiny — only unacknowledged, live rows are indexed.
        Index(
            "ix_task_step_ack_pending_by_worker",
            "workspace_id",
            "worker_id",
            postgresql_where=text("acknowledged_at IS NULL AND is_deleted = false"),
        ),
    )
