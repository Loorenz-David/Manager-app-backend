from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class User(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "usr"
    __tablename__ = "users"

    # Timestamps & provenance
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", deferrable=True), nullable=True
    )

    # Identity
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Localisation
    languages: Mapped[str | None] = mapped_column(String(512), nullable=True)
    language_preference: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Profile
    profile_picture: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Presence
    online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_online: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # FK shortcuts — updated atomically with the new child record
    last_app_view_record_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "user_app_view_records.client_id",
            name="fk_users_last_app_view_record_id",
            use_alter=True,
            deferrable=True,
        ),
        nullable=True,
    )
    last_history_record_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "user_history_records.client_id",
            name="fk_users_last_history_record_id",
            use_alter=True,
            deferrable=True,
        ),
        nullable=True,
    )
    # Relationships
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        primaryjoin="User.created_by_id == User.client_id",
    )
    app_view_records: Mapped[list["UserAppViewRecord"]] = relationship(
        "UserAppViewRecord",
        foreign_keys="[UserAppViewRecord.user_id]",
        back_populates="user",
    )
    user_history_records: Mapped[list["UserHistoryRecord"]] = relationship(
        "UserHistoryRecord",
        foreign_keys="[UserHistoryRecord.user_id]",
        back_populates="user",
    )
    last_app_view_record: Mapped["UserAppViewRecord | None"] = relationship(
        "UserAppViewRecord",
        foreign_keys=[last_app_view_record_id],
    )
    last_history_record: Mapped["UserHistoryRecord | None"] = relationship(
        "UserHistoryRecord",
        foreign_keys=[last_history_record_id],
    )
