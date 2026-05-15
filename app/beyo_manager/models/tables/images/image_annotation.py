from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.images.enums import ImageAnnotationTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ImageAnnotation(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ian"
    __tablename__ = "image_annotations"

    image_id: Mapped[str] = mapped_column(String(64), ForeignKey("images.client_id", deferrable=True), nullable=False, index=True)
    annotation_type: Mapped[ImageAnnotationTypeEnum] = mapped_column(
        SAEnum(ImageAnnotationTypeEnum, name="image_annotation_type_enum", create_type=True),
        nullable=False,
    )
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    accuracy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    image: Mapped["Image"] = relationship("Image", back_populates="image_annotations")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
