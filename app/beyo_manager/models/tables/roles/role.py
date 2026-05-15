from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class Role(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "role"
    __tablename__ = "roles"

    name: Mapped[RoleNameEnum] = mapped_column(
        SAEnum(RoleNameEnum, name="role_name_enum", create_type=True),
        nullable=False,
        unique=True,
        index=True,
    )
