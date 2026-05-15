from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ContentMentionLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "cml"
    __tablename__ = "content_mention_links"

    content_mention_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("content_mentions.client_id", deferrable=True), nullable=False, index=True
    )
    entity_type: Mapped[ContentMentionLinkEntityTypeEnum] = mapped_column(
        SAEnum(ContentMentionLinkEntityTypeEnum, name="content_mention_link_entity_type_enum", create_type=True),
        nullable=False,
        index=True,
    )
    entity_client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    @declared_attr
    def created_by_id(cls) -> Mapped[str]:
        return mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)

    content_mention: Mapped["ContentMention"] = relationship("ContentMention", foreign_keys=[content_mention_id], back_populates="links")
    created_by: Mapped["User"] = relationship("User", foreign_keys="[ContentMentionLink.created_by_id]")
