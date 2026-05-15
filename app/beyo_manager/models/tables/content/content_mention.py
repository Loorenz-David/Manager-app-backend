from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class ContentMention(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "cmt"
    __tablename__ = "content_mentions"
    __table_args__ = (
        UniqueConstraint("mention_table", "mention_id", name="uq_content_mention"),
    )

    mention_table: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    mention_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    links: Mapped[list["ContentMentionLink"]] = relationship(
        "ContentMentionLink",
        foreign_keys="[ContentMentionLink.content_mention_id]",
        back_populates="content_mention",
    )
