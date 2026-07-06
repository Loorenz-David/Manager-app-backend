from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin

if TYPE_CHECKING:
    from beyo_manager.models.tables.users.user import User


class Notification(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ntf"
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "read_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False, index=True
    )

    notification_type: Mapped[str] = mapped_column(String(64),  nullable=False, index=True)
    title:             Mapped[str] = mapped_column(String(256), nullable=False)
    body:              Mapped[str] = mapped_column(Text,        nullable=False)

    # Deep-link target
    entity_type:      Mapped[str | None] = mapped_column(String(64),  nullable=True)
    entity_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    read_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]        = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
