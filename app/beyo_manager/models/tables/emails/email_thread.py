from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailThread(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "eth"
    __tablename__ = "email_threads"
    __table_args__ = (
        Index("ix_email_threads_entity", "entity_type", "entity_client_id"),
        Index("ix_email_threads_major_entity", "major_entity_type", "major_entity_client_id"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True
    )
    connection_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("email_connections.client_id"), nullable=False, index=True
    )
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    major_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    major_entity_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subject_normalized: Mapped[str | None] = mapped_column(String(512), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_inbound_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True
    )

    messages: Mapped[list["EmailMessage"]] = relationship(
        "EmailMessage", back_populates="thread", lazy="raise"
    )
    user_states: Mapped[list["EmailThreadUserState"]] = relationship(
        "EmailThreadUserState", back_populates="thread", lazy="raise"
    )
