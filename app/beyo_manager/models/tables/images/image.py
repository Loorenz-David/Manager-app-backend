from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.images.enums import ImageSourceReferenceEnum, ImageSourceTypeEnum, ImageStorageProviderEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class Image(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "img"
    __tablename__ = "images"

    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_provider: Mapped[ImageStorageProviderEnum] = mapped_column(
        SAEnum(ImageStorageProviderEnum, name="image_storage_provider_enum", create_type=True),
        nullable=False,
        index=True,
    )
    source_type: Mapped[ImageSourceTypeEnum] = mapped_column(
        SAEnum(ImageSourceTypeEnum, name="image_source_type_enum", create_type=True),
        nullable=False,
    )
    source_reference: Mapped[ImageSourceReferenceEnum | None] = mapped_column(
        SAEnum(ImageSourceReferenceEnum, name="image_source_reference_enum", create_type=True),
        nullable=True,
    )
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)
    updated_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_event_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("image_events.client_id", use_alter=True, name="fk_image_last_event_id", deferrable=True),
        nullable=True,
    )

    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    updated_by: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_id])
    deleted_by: Mapped["User | None"] = relationship("User", foreign_keys=[deleted_by_id])
    image_links: Mapped[list["ImageLink"]] = relationship("ImageLink", back_populates="image")
    image_annotations: Mapped[list["ImageAnnotation"]] = relationship("ImageAnnotation", back_populates="image")
    events: Mapped[list["ImageEvent"]] = relationship("ImageEvent", foreign_keys="[ImageEvent.image_id]", back_populates="image")
    last_event: Mapped["ImageEvent | None"] = relationship("ImageEvent", foreign_keys=[last_event_id])
