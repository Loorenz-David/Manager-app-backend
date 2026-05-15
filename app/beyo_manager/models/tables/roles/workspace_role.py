from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkspaceRole(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "wsr"
    __tablename__ = "workspace_roles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_roles_workspace_name"),
    )

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", deferrable=True), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(64), ForeignKey("roles.client_id", deferrable=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    role: Mapped["Role"] = relationship("Role")
