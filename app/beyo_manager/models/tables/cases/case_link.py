from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseLinkRoleEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class CaseLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "clk"
    __tablename__ = "case_links"
    __table_args__ = (
        UniqueConstraint("case_id", "entity_type", "entity_client_id", name="uq_case_link_case_entity"),
    )

    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.client_id", deferrable=True), nullable=False, index=True)
    entity_type: Mapped[CaseLinkEntityTypeEnum] = mapped_column(
        SAEnum(CaseLinkEntityTypeEnum, name="case_link_entity_type_enum", create_type=False),
        nullable=False,
        index=True,
    )
    entity_client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[CaseLinkRoleEnum] = mapped_column(
        SAEnum(CaseLinkRoleEnum, name="case_link_role_enum", create_type=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id], back_populates="links")
