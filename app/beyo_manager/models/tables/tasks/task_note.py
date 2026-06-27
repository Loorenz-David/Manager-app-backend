from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import TaskNoteTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class TaskNote(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tno"
    __tablename__ = "task_notes"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    note_type: Mapped[TaskNoteTypeEnum] = mapped_column(
        SAEnum(TaskNoteTypeEnum, name="task_note_type_enum", create_type=True), nullable=False
    )
    content: Mapped[list | dict] = mapped_column(JSON, nullable=False)
    plain_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    users_read_list: Mapped[list | None] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (Index("ix_task_notes_workspace_task_created", "workspace_id", "task_id", "created_at"),)
