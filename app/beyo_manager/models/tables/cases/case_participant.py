from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class CaseParticipant(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "cpa"
    __tablename__ = "case_participants"
    __table_args__ = (
        UniqueConstraint("case_id", "user_id", name="uq_case_participant"),
    )

    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.client_id", deferrable=True), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)
    last_read_message_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id], back_populates="participants")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
