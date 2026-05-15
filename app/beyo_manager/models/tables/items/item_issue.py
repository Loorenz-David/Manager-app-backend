from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.items.enums import ItemIssueStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ItemIssue(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "iti"
    __tablename__ = "item_issues"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("items.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issue_type_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("issue_types.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    issue_severity_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("issue_severities.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    state: Mapped[ItemIssueStateEnum] = mapped_column(
        SAEnum(ItemIssueStateEnum, name="item_issue_state_enum", create_type=True),
        nullable=False,
        default=ItemIssueStateEnum.PENDING,
        index=True,
    )
    base_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    issue_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        Index("ix_item_issues_workspace_state", "workspace_id", "state"),
        Index("ix_item_issues_workspace_item_state", "workspace_id", "item_id", "state"),
        CheckConstraint(
            "base_time_seconds IS NULL OR base_time_seconds >= 0",
            name="ck_item_issues_base_time_positive",
        ),
        CheckConstraint(
            "time_multiplier IS NULL OR time_multiplier >= 0",
            name="ck_item_issues_time_multiplier_positive",
        ),
    )
