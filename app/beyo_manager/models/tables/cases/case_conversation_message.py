from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class CaseConversationMessage(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ccm"
    __tablename__ = "case_conversation_messages"
    __table_args__ = (
        UniqueConstraint("case_conversation_id", "message_seq", name="uq_message_seq"),
    )

    case_conversation_id: Mapped[str] = mapped_column(String(64), ForeignKey("case_conversations.client_id", deferrable=True), nullable=False, index=True)
    message_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    @declared_attr
    def created_by_id(cls) -> Mapped[str]:
        return mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)

    content: Mapped[list | dict] = mapped_column(JSONB, nullable=False)
    plain_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    has_been_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_been_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    conversation: Mapped["CaseConversation"] = relationship("CaseConversation", foreign_keys=[case_conversation_id], back_populates="messages")
    created_by: Mapped["User"] = relationship("User", foreign_keys="[CaseConversationMessage.created_by_id]")
