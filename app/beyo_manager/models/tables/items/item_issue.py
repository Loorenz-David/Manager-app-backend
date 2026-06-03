from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class ItemIssue(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "iti"
    __tablename__ = "item_issues"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("items.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("task_steps.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    worker_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_category_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("item_categories.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issue_type_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("issue_types.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    issue_type_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_mode_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    placement_of_issue_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
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
        Index("ix_item_issues_workspace_item", "workspace_id", "item_id"),
        Index("ix_item_issues_workspace_step", "workspace_id", "step_id"),
        CheckConstraint(
            "intensity >= 1",
            name="ck_item_issues_intensity_positive",
        ),
    )
