from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class ImageLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "iml"
    __tablename__ = "image_links"
    __table_args__ = (
        UniqueConstraint("image_id", "entity_type", "entity_client_id", name="uq_image_link_image_entity"),
    )

    image_id: Mapped[str] = mapped_column(String(64), ForeignKey("images.client_id", deferrable=True), nullable=False, index=True)
    entity_type: Mapped[ImageLinkEntityTypeEnum] = mapped_column(
        SAEnum(ImageLinkEntityTypeEnum, name="image_link_entity_type_enum", create_type=True),
        nullable=False,
        index=True,
    )
    entity_client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    image: Mapped["Image"] = relationship("Image", back_populates="image_links")
