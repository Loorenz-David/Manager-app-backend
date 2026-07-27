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
    SlideLayoutEnum,
    SlidePlaybackModeEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class AppUpdatePresentationSlide(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "aups"
    __tablename__ = "app_update_presentation_slides"

    presentation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("app_update_presentations.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    layout_type: Mapped[SlideLayoutEnum] = mapped_column(
        SAEnum(SlideLayoutEnum, name="app_update_slide_layout_enum", create_type=True),
        nullable=False,
        default=SlideLayoutEnum.MEDIA_TOP,
    )
    action_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    action_route: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # --- Timeline composition ---
    playback_mode: Mapped[SlidePlaybackModeEnum] = mapped_column(
        SAEnum(SlidePlaybackModeEnum, name="app_update_slide_playback_mode_enum", create_type=True),
        nullable=False,
        default=SlidePlaybackModeEnum.MANUAL,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    composition_schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    background_color: Mapped[str | None] = mapped_column(String(9), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    presentation: Mapped["AppUpdatePresentation"] = relationship(
        "AppUpdatePresentation", back_populates="slides", lazy="raise"
    )
    media: Mapped[list["AppUpdateSlideMedia"]] = relationship(
        "AppUpdateSlideMedia", back_populates="slide", lazy="raise"
    )
    elements: Mapped[list["AppUpdateSlideElement"]] = relationship(
        "AppUpdateSlideElement", back_populates="slide", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint(
            "presentation_id", "sequence_order", name="uq_app_update_slides_presentation_sequence"
        ),
        Index("ix_app_update_slides_presentation_sequence", "presentation_id", "sequence_order"),
    )
