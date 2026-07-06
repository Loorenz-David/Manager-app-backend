from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin

if TYPE_CHECKING:
    from beyo_manager.models.tables.emails.email_thread import EmailThread


class EmailMessage(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "emsg"
    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "provider_folder",
            "provider_uid",
            name="uq_email_message_provider_uid",
        ),
        Index("ix_email_messages_rfc_id", "rfc_message_id"),
        Index("ix_email_messages_thread_time", "thread_id", "sent_or_received_at"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True
    )
    connection_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("email_connections.client_id"), nullable=False, index=True
    )
    thread_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("email_threads.client_id"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    provider_folder: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_uid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_addresses_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    cc_addresses_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    bcc_addresses_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_body_clean: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_preview: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rfc_message_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(512), nullable=True)
    references_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tracking_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_headers_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sent_or_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    send_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    send_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    thread: Mapped["EmailThread"] = relationship("EmailThread", back_populates="messages", lazy="raise")
