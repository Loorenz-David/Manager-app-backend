from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailConnection(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ecn"
    __tablename__ = "email_connections"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True
    )
    owner_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False, index=True
    )
    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False)
    smtp_security: Mapped[str] = mapped_column(String(16), nullable=False)
    smtp_username: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_password_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False)
    imap_security: Mapped[str] = mapped_column(String(16), nullable=False)
    imap_username: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_password_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    inbox_folder: Mapped[str] = mapped_column(
        String(128), nullable=False, default="INBOX", server_default="INBOX"
    )
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sync_state: Mapped["EmailSyncState | None"] = relationship(
        "EmailSyncState", back_populates="connection", uselist=False, lazy="raise"
    )
