from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailSyncState(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "esyn"
    __tablename__ = "email_sync_states"

    connection_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("email_connections.client_id"), nullable=False, unique=True, index=True
    )
    folder: Mapped[str] = mapped_column(
        String(128), nullable=False, default="INBOX", server_default="INBOX"
    )
    uidvalidity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_uid: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True
    )

    connection: Mapped["EmailConnection"] = relationship(
        "EmailConnection", back_populates="sync_state", lazy="raise"
    )
