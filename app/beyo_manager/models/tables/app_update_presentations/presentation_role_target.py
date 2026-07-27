from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class AppUpdatePresentationRoleTarget(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "auprt"
    __tablename__ = "app_update_presentation_role_targets"

    presentation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("app_update_presentations.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role_key: Mapped[RoleNameEnum] = mapped_column(
        SAEnum(RoleNameEnum, name="app_update_role_key_enum", create_type=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    presentation: Mapped["AppUpdatePresentation"] = relationship(
        "AppUpdatePresentation", back_populates="role_targets", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint(
            "presentation_id", "role_key", name="uq_app_update_role_targets_presentation_role"
        ),
    )
