from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class NotificationPin(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "npin"
    __tablename__ = "notification_pins"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "entity_type", "entity_client_id",
            name="uq_notification_pin_user_entity",
        ),
    )

    user_id:          Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False, index=True
    )
    entity_type:      Mapped[str] = mapped_column(String(64),  nullable=False, index=True)
    entity_client_id: Mapped[str] = mapped_column(String(128), nullable=False)

    pinned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
