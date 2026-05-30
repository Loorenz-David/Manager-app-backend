from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from beyo_manager.domain.cases.enums import CaseStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.history_record import HistoryRecordMixin
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class Case(IdentityMixin, HistoryRecordMixin, Base):
    CLIENT_ID_PREFIX = "ca"
    __tablename__ = "cases"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @declared_attr
    def created_by_id(cls) -> Mapped[str]:
        return mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)

    state: Mapped[CaseStateEnum] = mapped_column(
        SAEnum(CaseStateEnum, name="case_state_enum", create_type=True),
        nullable=False,
        default=CaseStateEnum.OPEN,
        index=True,
    )
    case_type_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("case_types.client_id", deferrable=True, ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    participants_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversations_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    case_type: Mapped["CaseType | None"] = relationship("CaseType", foreign_keys=[case_type_id], back_populates="cases")
    created_by: Mapped["User"] = relationship("User", foreign_keys="[Case.created_by_id]")
    updated_by: Mapped["User"] = relationship("User", foreign_keys="[Case.updated_by_id]")
    participants: Mapped[list["CaseParticipant"]] = relationship("CaseParticipant", foreign_keys="[CaseParticipant.case_id]", back_populates="case")
    conversations: Mapped[list["CaseConversation"]] = relationship("CaseConversation", foreign_keys="[CaseConversation.case_id]", back_populates="case")
    links: Mapped[list["CaseLink"]] = relationship("CaseLink", foreign_keys="[CaseLink.case_id]", back_populates="case")
