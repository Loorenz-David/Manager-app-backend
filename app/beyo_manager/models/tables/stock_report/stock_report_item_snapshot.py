"""`stock_report_item_snapshots` — one row's frozen demand inside one version.

`quantity_requested` is the value that is set in stone at creation. The three counters
are copied at creation and **overwritten when the snapshot closes**; while the snapshot
is active the live values are the row's own (`serialize_stock_report_item_snapshot`
reads them from the row), so `move_assignment` never writes here. `priority` and
`priority_order` live here, not on the row: every version starts unprioritised and is
ordered by hand or copied from a previous version. `quantity_missing` is always 0 on a
fresh snapshot — a new version is a re-assessment.

A snapshot is active while `closed_at IS NULL`; it closes with its version, or alone
when its row is deleted mid-version (`cascade_delete_stock_report_item`).
"""

from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class StockReportItemSnapshot(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "srs"
    __tablename__ = "stock_report_item_snapshots"
    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("stock_report_snapshot_versions.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stock_report_item_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("stock_report_items.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_requested: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quantity_in_queue: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quantity_in_progress: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quantity_awaiting: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quantity_missing: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Units of this row's assignments that Scanner resolved (`resolved` /
    # `resolved_early`) while the snapshot was active. Monotonic — terminal states are
    # never left — and never frozen or zeroed: it is the version's completion memory.
    # The wire `quantity_awaiting` is the live/frozen awaiting **plus** this (owner
    # ruling 2026-09-26: completion never decrements on resolve).
    quantity_resolved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    priority: Mapped[StockReportPriorityEnum | None] = mapped_column(
        SAEnum(
            StockReportPriorityEnum, name="stock_report_priority_enum", create_type=True
        ),
        nullable=True,
    )
    priority_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    __table_args__ = (
        Index(
            "uix_stock_report_item_snapshots_row_active",
            "workspace_id",
            "stock_report_item_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
        ),
        UniqueConstraint(
            "version_id",
            "stock_report_item_id",
            name="uq_stock_report_item_snapshots_version_row",
        ),
        Index(
            "ix_stock_report_item_snapshots_workspace_priority_order",
            "workspace_id",
            "priority",
            "priority_order",
            postgresql_where=text("closed_at IS NULL"),
        ),
        CheckConstraint(
            "quantity_requested >= 0",
            name="ck_stock_report_item_snapshots_quantity_requested_nonneg",
        ),
        CheckConstraint(
            "quantity_in_queue >= 0",
            name="ck_stock_report_item_snapshots_quantity_in_queue_nonneg",
        ),
        CheckConstraint(
            "quantity_in_progress >= 0",
            name="ck_stock_report_item_snapshots_quantity_in_progress_nonneg",
        ),
        CheckConstraint(
            "quantity_awaiting >= 0",
            name="ck_stock_report_item_snapshots_quantity_awaiting_nonneg",
        ),
        CheckConstraint(
            "quantity_missing >= 0",
            name="ck_stock_report_item_snapshots_quantity_missing_nonneg",
        ),
        CheckConstraint(
            "quantity_resolved >= 0",
            name="ck_stock_report_item_snapshots_quantity_resolved_nonneg",
        ),
        CheckConstraint(
            "(priority IS NULL) = (priority_order IS NULL)",
            name="ck_stock_report_item_snapshots_priority_order_pairing",
        ),
    )
