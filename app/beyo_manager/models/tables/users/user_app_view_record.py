from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserAppViewRecord(IdentityMixin, Base):
    """One row per continuous visit a user spends viewing an entity.

    entity_type must be an EntityType enum value (defined in Phase 7).
    entity_client_id is None for list-page views — use workspace client_id instead.
    """
    CLIENT_ID_PREFIX = "uavr"
    __tablename__ = "user_app_view_records"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="app_view_records",
    )
