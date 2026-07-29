from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserDeclaredStateRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uds"
    __tablename__ = "user_declared_state_records"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pause_reason_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("pause_reasons.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False
    )
    closed_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "exited_at IS NULL OR exited_at >= entered_at",
            name="ck_user_declared_state_records_exited_after_entered",
        ),
        Index(
            "ix_user_declared_state_records_user_workspace_entered",
            "user_id",
            "workspace_id",
            "entered_at",
        ),
        Index(
            "ix_user_declared_state_records_workspace_reason",
            "workspace_id",
            "pause_reason_id",
        ),
        Index(
            "uix_user_declared_state_records_active",
            "user_id",
            "workspace_id",
            unique=True,
            postgresql_where=text("exited_at IS NULL"),
        ),
    )
