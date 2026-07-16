from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkingSectionMembership(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "wsme"
    __tablename__ = "working_section_memberships"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Per-user ordering of their active sections within a workspace (lower = higher priority).
    # Dense 0-based, maintained as an application invariant by the working-section membership
    # commands (no DB unique constraint: row-by-row reorders would hit transient collisions).
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_by_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_working_section_memberships_user_removed", "user_id", "removed_at"),
        Index("ix_working_section_memberships_section_removed", "working_section_id", "removed_at"),
        Index(
            "uix_working_section_memberships_active",
            "workspace_id",
            "working_section_id",
            "user_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )
