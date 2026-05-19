from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.history.enums import HistoryRecordEntityTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class HistoryRecordLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "hrlk"
    __tablename__ = "history_record_links"

    history_record_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("history_records.client_id", deferrable=True), nullable=False, index=True
    )
    entity_type: Mapped[HistoryRecordEntityTypeEnum] = mapped_column(
        SAEnum(HistoryRecordEntityTypeEnum, name="history_record_entity_type_enum", create_type=False),
        nullable=False,
        index=True,
    )
    entity_client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    history_record: Mapped["HistoryRecord"] = relationship(
        "HistoryRecord",
        back_populates="link",
    )

    __table_args__ = (
        Index(
            "ix_history_record_links_entity_type_client_id",
            "entity_type",
            "entity_client_id",
        ),
    )
