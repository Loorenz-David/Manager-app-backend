from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from beyo_manager.domain.cases.enums import CaseStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class CaseConversation(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ccv"
    __tablename__ = "case_conversations"

    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.client_id", deferrable=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    @declared_attr
    def created_by_id(cls) -> Mapped[str]:
        return mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)

    state: Mapped[CaseStateEnum] = mapped_column(
        SAEnum(CaseStateEnum, name="case_state_enum", create_type=False),
        nullable=False,
        default=CaseStateEnum.OPEN,
        index=True,
    )
    last_message_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id], back_populates="conversations")
    created_by: Mapped["User"] = relationship("User", foreign_keys="[CaseConversation.created_by_id]")
    messages: Mapped[list["CaseConversationMessage"]] = relationship(
        "CaseConversationMessage",
        foreign_keys="[CaseConversationMessage.case_conversation_id]",
        back_populates="conversation",
        order_by="CaseConversationMessage.message_seq",
    )
