from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkspaceMembership(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "wsm"
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_workspace_memberships_user_workspace"),
    )

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", deferrable=True), nullable=False, index=True)
    workspace_role_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspace_roles.client_id", deferrable=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    workspace_role: Mapped["WorkspaceRole"] = relationship("WorkspaceRole")
