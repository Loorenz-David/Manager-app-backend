from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class PauseReason(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "par"
    __tablename__ = "pause_reasons"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pause_type: Mapped[PauseTypeEnum] = mapped_column(
        SAEnum(PauseTypeEnum, name="pause_reason_type_enum", create_type=True), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    requires_description: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_system_managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_pause_reasons_workspace_name"),
        Index("uq_pause_reasons_slug", "slug", unique=True),
        Index("ix_pause_reasons_workspace_type", "workspace_id", "pause_type"),
    )
