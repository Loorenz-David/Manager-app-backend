from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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
        Index(
            "ix_notification_pins_major_entity",
            "major_entity_type",
            "major_client_entity_id",
        ),
    )

    user_id:          Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False, index=True
    )
    entity_type:      Mapped[str] = mapped_column(String(64),  nullable=False, index=True)
    entity_client_id: Mapped[str] = mapped_column(String(128), nullable=False)
    conditions:       Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    fire_once:        Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    major_entity_type:      Mapped[str | None] = mapped_column(String(64), nullable=True)
    major_client_entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    pinned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
