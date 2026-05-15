from sqlalchemy import String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class CaseType(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "cty"
    __tablename__ = "case_types"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    entity_type: Mapped[CaseLinkEntityTypeEnum] = mapped_column(
        SAEnum(CaseLinkEntityTypeEnum, name="case_link_entity_type_enum", create_type=True),
        nullable=False,
        index=True,
    )

    cases: Mapped[list["Case"]] = relationship("Case", foreign_keys="[Case.case_type_id]", back_populates="case_type")
