from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class SkuTemplate(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "skt"
    __tablename__ = "sku_templates"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_type: Mapped[TaskTypeEnum] = mapped_column(
        SAEnum(TaskTypeEnum, name="business_task_type_enum", create_type=False), nullable=False
    )
    prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    separator: Mapped[str] = mapped_column(String(8), nullable=False, default="-")
    pad_width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scalar: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index(
            "uix_sku_templates_workspace_task_type",
            "workspace_id",
            "task_type",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )
