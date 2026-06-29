from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.workspaces.enums import WorkspaceSpecializationEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class WorkspaceRole(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "wsr"
    __tablename__ = "workspace_roles"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "role_id",
            "specialization",
            name="uq_workspace_roles_workspace_role_specialization",
        ),
    )

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", deferrable=True), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(64), ForeignKey("roles.client_id", deferrable=True), nullable=False, index=True)
    specialization: Mapped[WorkspaceSpecializationEnum | None] = mapped_column(
        SAEnum(
            WorkspaceSpecializationEnum,
            name="workspace_role_specialization_enum",
            create_type=False,
        ),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    role: Mapped["Role"] = relationship("Role")
