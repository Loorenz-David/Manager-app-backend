from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailThreadUserState(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "etus"
    __tablename__ = "email_thread_user_states"
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_email_thread_user_state"),
    )

    thread_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("email_threads.client_id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False, index=True
    )
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    muted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True
    )

    thread: Mapped["EmailThread"] = relationship("EmailThread", back_populates="user_states", lazy="raise")
