from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class HistoryRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "hrec"
    __tablename__ = "history_records"

    change_type: Mapped[HistoryRecordChangeTypeEnum] = mapped_column(
        SAEnum(HistoryRecordChangeTypeEnum, name="history_record_change_type_enum", create_type=False),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    from_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    to_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", deferrable=True), nullable=True, index=True
    )

    username_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)

    link: Mapped["HistoryRecordLink | None"] = relationship(
        "HistoryRecordLink",
        back_populates="history_record",
        uselist=False,
    )
