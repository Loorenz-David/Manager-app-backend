from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.history_record import HistoryRecord
from beyo_manager.models.base.identity import IdentityMixin


class UserHistoryRecord(IdentityMixin, HistoryRecord, Base):
    CLIENT_ID_PREFIX = "uhr"
    __tablename__ = "user_history_records"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="user_history_records",
    )
    updated_by: Mapped["User"] = relationship(
        "User",
        foreign_keys="[UserHistoryRecord.updated_by_id]",
    )
