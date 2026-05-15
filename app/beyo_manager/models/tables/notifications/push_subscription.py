from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class PushSubscription(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "psub"
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", name="uq_push_subscription_user_endpoint"),
    )

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False, index=True
    )

    endpoint:     Mapped[str]        = mapped_column(Text,        nullable=False)
    p256dh:       Mapped[str]        = mapped_column(Text,        nullable=False)
    auth:         Mapped[str]        = mapped_column(Text,        nullable=False)
    device_label: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
