from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class AppUpdatePresentationUserTarget(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "auput"
    __tablename__ = "app_update_presentation_user_targets"

    presentation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("app_update_presentations.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    presentation: Mapped["AppUpdatePresentation"] = relationship(
        "AppUpdatePresentation", back_populates="user_targets", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint(
            "presentation_id", "user_id", name="uq_app_update_user_targets_presentation_user"
        ),
    )
