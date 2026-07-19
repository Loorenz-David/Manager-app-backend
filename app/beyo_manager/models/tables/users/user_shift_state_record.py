from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UserShiftStateRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uss"
    __tablename__ = "user_shift_state_records"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[UserShiftStateEnum] = mapped_column(
        SAEnum(UserShiftStateEnum, name="user_shift_state_enum", create_type=True), nullable=False
    )
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    changed_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    manually_recorded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    __table_args__ = (
        CheckConstraint(
            "exited_at IS NULL OR exited_at >= entered_at",
            name="ck_user_shift_state_records_exited_after_entered",
        ),
        Index("ix_user_shift_state_records_user_workspace_entered", "user_id", "workspace_id", "entered_at"),
        Index("ix_user_shift_state_records_user_workspace_exited", "user_id", "workspace_id", "exited_at"),
        Index(
            "uix_user_shift_state_records_active",
            "user_id",
            "workspace_id",
            unique=True,
            postgresql_where=text("exited_at IS NULL"),
        ),
    )
