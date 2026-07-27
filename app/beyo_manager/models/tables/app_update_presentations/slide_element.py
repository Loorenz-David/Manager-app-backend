from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.app_update_presentations.enums import SlideElementTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class AppUpdateSlideElement(IdentityMixin, Base):
    """One timed, layered element on a slide's timeline.

    Text and media are independent, composable elements. A ``media`` element
    references an ``AppUpdateSlideMedia`` asset (which owns storage/intrinsic
    data); the element owns placement, timing, layer, layout, style, and
    animation. A ``text`` element owns its own ``text_content``.
    """

    CLIENT_ID_PREFIX = "aupe"
    __tablename__ = "app_update_slide_elements"

    slide_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("app_update_presentation_slides.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    element_type: Mapped[SlideElementTypeEnum] = mapped_column(
        SAEnum(SlideElementTypeEnum, name="app_update_slide_element_type_enum", create_type=True),
        nullable=False,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    layer_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # media element payload
    media_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("app_update_slide_media.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # text element payload
    text_content: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    # validated JSON config (see domain/app_update_presentations/composition_schemas.py)
    layout: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    style: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    enter_animation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exit_animation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    slide: Mapped["AppUpdatePresentationSlide"] = relationship(
        "AppUpdatePresentationSlide", back_populates="elements", lazy="raise"
    )
    media: Mapped["AppUpdateSlideMedia | None"] = relationship(
        "AppUpdateSlideMedia", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint(
            "slide_id", "sequence_order", name="uq_app_update_slide_elements_slide_sequence"
        ),
        # Primary read pattern: all elements of a slide, in deterministic order.
        Index(
            "ix_app_update_slide_elements_order",
            "slide_id",
            "layer_index",
            "sequence_order",
            "start_ms",
        ),
        # Safe scalar timing invariants (structural rules live in the domain layer).
        CheckConstraint("start_ms >= 0", name="ck_app_update_slide_elements_start_non_negative"),
        CheckConstraint(
            "end_ms IS NULL OR end_ms > start_ms",
            name="ck_app_update_slide_elements_end_after_start",
        ),
    )
