from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.images.enums import ImageEventErrorEnum, ImageEventTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.event import Event
from beyo_manager.models.base.identity import IdentityMixin


class ImageEvent(IdentityMixin, Event, Base):
    CLIENT_ID_PREFIX = "iev"
    EVENT_TYPE_ENUM = ImageEventTypeEnum
    EVENT_ERROR_ENUM = ImageEventErrorEnum
    __tablename__ = "image_events"

    image_id: Mapped[str] = mapped_column(String(64), ForeignKey("images.client_id", deferrable=True), nullable=False, index=True)

    image: Mapped["Image"] = relationship("Image", foreign_keys=[image_id], back_populates="events")
    created_by: Mapped["User"] = relationship("User", foreign_keys="[ImageEvent.created_by_id]")
