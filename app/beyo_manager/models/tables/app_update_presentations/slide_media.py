from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.app_update_presentations.enums import SlideMediaTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class AppUpdateSlideMedia(IdentityMixin, Base):
    """One media item on a slide. ``storage_key`` holds the S3 object key — never
    a presigned URL. A carousel is several ordered image rows on one slide."""

    CLIENT_ID_PREFIX = "aupm"
    __tablename__ = "app_update_slide_media"

    slide_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("app_update_presentation_slides.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[SlideMediaTypeEnum] = mapped_column(
        SAEnum(SlideMediaTypeEnum, name="app_update_slide_media_type_enum", create_type=True),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(2048), nullable=False)
    poster_storage_key: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    fallback_storage_key: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_looping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    slide: Mapped["AppUpdatePresentationSlide"] = relationship(
        "AppUpdatePresentationSlide", back_populates="media", lazy="raise"
    )

    __table_args__ = (
        # Partial: a soft-deleted row keeps its historical sequence_order but
        # reserves nothing, so the slot is free for the next active media.
        Index(
            "uix_app_update_slide_media_slide_sequence_active",
            "slide_id",
            "sequence_order",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index("ix_app_update_slide_media_slide_sequence", "slide_id", "sequence_order"),
    )
