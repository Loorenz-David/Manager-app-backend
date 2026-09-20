from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class StockTaskAssignment(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "sta"
    __tablename__ = "stock_task_assignments"
    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stock_report_item_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("stock_report_items.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tasks.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("items.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    credited_history_record_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("stock_report_history_records.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    property_mismatch_overridden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    state: Mapped[StockTaskAssignmentStateEnum] = mapped_column(
        SAEnum(
            StockTaskAssignmentStateEnum,
            name="stock_task_assignment_state_enum",
            create_type=True,
        ),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    __table_args__ = (
        Index(
            "uix_stock_task_assignments_item_active",
            "workspace_id",
            "item_id",
            unique=True,
            postgresql_where=text(
                "is_deleted = false AND state IN ('in_queue', 'in_progress', 'awaiting')"
            ),
        ),
        Index(
            "uix_stock_task_assignments_task_active",
            "workspace_id",
            "task_id",
            unique=True,
            postgresql_where=text(
                "is_deleted = false AND state IN ('in_queue', 'in_progress', 'awaiting')"
            ),
        ),
        Index("ix_stock_task_assignments_row_state", "stock_report_item_id", "state"),
        CheckConstraint(
            "quantity >= 1", name="ck_stock_task_assignments_quantity_positive"
        ),
    )
