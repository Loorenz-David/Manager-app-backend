from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.app_update_presentations.enums import (
    AudienceModeEnum,
    PresentationCategoryEnum,
    PresentationStatusEnum,
    PresentationTypeEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class AppUpdatePresentation(IdentityMixin, Base):
    """One immutable-once-published version of a logical update presentation.

    ``logical_client_id`` groups every version of the same announcement; the
    first draft sets it equal to its own ``client_id``. ``version`` increments
    per logical presentation. Published rows are immutable — content changes
    require a new draft version.
    """

    CLIENT_ID_PREFIX = "aup"
    __tablename__ = "app_update_presentations"

    logical_client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    status: Mapped[PresentationStatusEnum] = mapped_column(
        SAEnum(PresentationStatusEnum, name="app_update_presentation_status_enum", create_type=True),
        nullable=False,
        default=PresentationStatusEnum.DRAFT,
        index=True,
    )
    presentation_type: Mapped[PresentationTypeEnum] = mapped_column(
        SAEnum(PresentationTypeEnum, name="app_update_presentation_type_enum", create_type=True),
        nullable=False,
        default=PresentationTypeEnum.SLIDE_PAGE,
    )
    audience_mode: Mapped[AudienceModeEnum] = mapped_column(
        SAEnum(AudienceModeEnum, name="app_update_presentation_audience_mode_enum", create_type=True),
        nullable=False,
        default=AudienceModeEnum.ALL_MATCHING,
    )
    category: Mapped[PresentationCategoryEnum | None] = mapped_column(
        SAEnum(PresentationCategoryEnum, name="app_update_presentation_category_enum", create_type=True),
        nullable=True,
    )

    display_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    is_dismissible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    slides: Mapped[list["AppUpdatePresentationSlide"]] = relationship(
        "AppUpdatePresentationSlide",
        back_populates="presentation",
        lazy="raise",
    )
    app_targets: Mapped[list["AppUpdatePresentationAppTarget"]] = relationship(
        "AppUpdatePresentationAppTarget", back_populates="presentation", lazy="raise"
    )
    role_targets: Mapped[list["AppUpdatePresentationRoleTarget"]] = relationship(
        "AppUpdatePresentationRoleTarget", back_populates="presentation", lazy="raise"
    )
    workspace_targets: Mapped[list["AppUpdatePresentationWorkspaceTarget"]] = relationship(
        "AppUpdatePresentationWorkspaceTarget", back_populates="presentation", lazy="raise"
    )
    user_targets: Mapped[list["AppUpdatePresentationUserTarget"]] = relationship(
        "AppUpdatePresentationUserTarget", back_populates="presentation", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint(
            "logical_client_id", "version", name="uq_app_update_presentations_logical_version"
        ),
        Index(
            "ix_app_update_presentations_ws_status_priority",
            "workspace_id",
            "status",
            "display_priority",
        ),
        # Multiple published versions of one logical announcement may coexist;
        # the active/what's-new resolution serves the newest version each user is
        # eligible for (audience-scoped, newest-version-wins). This index speeds
        # the "highest version per logical announcement" lookup.
        Index(
            "ix_app_update_presentations_logical_version",
            "logical_client_id",
            "version",
        ),
    )
