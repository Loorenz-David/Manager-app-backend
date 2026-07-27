from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.app_update_presentations.enums import (
    PresentationViewStatusEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class AppUpdatePresentationView(IdentityMixin, Base):
    """Per-acting-user view state for one presentation version.

    Keyed by ``(presentation_id, acting_user_id)`` — ``presentation_id`` is
    version-specific, so the version is implicit. View state is per user (there
    is no device identity in this system). Absence of a row means "unseen".
    """

    CLIENT_ID_PREFIX = "aupv"
    __tablename__ = "app_update_presentation_views"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    presentation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("app_update_presentations.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    acting_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[PresentationViewStatusEnum] = mapped_column(
        SAEnum(
            PresentationViewStatusEnum,
            name="app_update_presentation_view_status_enum",
            create_type=True,
        ),
        nullable=False,
        default=PresentationViewStatusEnum.SHOWN,
    )
    first_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_slide_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "presentation_id",
            "acting_user_id",
            name="uq_app_update_presentation_views_presentation_user",
        ),
        # Hot anti-join for the active-eligibility query: a user's incomplete views.
        Index(
            "ix_app_update_presentation_views_user_incomplete",
            "acting_user_id",
            "presentation_id",
            postgresql_where=text("completed_at IS NULL"),
        ),
    )
