"""`stock_report_item_snapshots` — one row's place inside one version.

Since the draft versions change (2026-09-28) a version has three states, derived
from two dates on the version **and denormalised onto every one of its snapshots**
(`active_at`, `closed_at`, so the partial indexes and per-snapshot predicates need no
join): a **draft** (`active_at IS NULL`), the **active** version (`active_at IS NOT
NULL AND closed_at IS NULL`) and a **closed** one. Two predicates therefore exist and
are never hand-typed (`services/commands/stock_report/_predicates.py`): *open*
(`closed_at IS NULL`, drafts included — the counters' live-or-frozen switch) and
*active* (the pair — everything that means "the board").

The requested quantity is two columns and one derived value:

* `quantity_requested_scanner` — Scanner's value **frozen at activation** (or at a
  direct active create, or re-frozen by a refresh). NULL exactly while the version is
  a draft (`ck_…_scanner_iff_activated`): a draft is live and reads the row.
* `quantity_requested_manual` — the user's override, NULL when none.
* the wire `quantity_requested` = `COALESCE(manual, CASE WHEN draft THEN row.quantity_requested
  ELSE scanner END)` (`snapshot_rules.effective_quantity_requested`).

`quantity_missing` is NULL only on a draft snapshot the user has typed nothing for
(`ck_…_missing_set_once_activated`); such a row **borrows** the active version's
number on every read. `priority` / `priority_order` live here, not on the row. The
three counters are copied at creation and overwritten when the snapshot closes;
while it is open the live values are the row's own, so `move_assignment` never writes
here.

A snapshot closes with its version, or alone when its row is deleted while the
version is active; a **draft's** snapshot is hard-deleted instead (`closed_at` implies
`active_at`, `ck_…_closed_implies_activated`).
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

# The SQL of the two lifecycle predicates, shared with the migration and the
# `_predicates` module so one spelling exists.
ACTIVE_SNAPSHOT_WHERE = "active_at IS NOT NULL AND closed_at IS NULL"
OPEN_SNAPSHOT_WHERE = "closed_at IS NULL"


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
    # Scanner's value frozen at activation; NULL exactly while the version is a
    # draft. No default on purpose: every writer decides (a draft writes NULL).
    quantity_requested_scanner: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    # The user's override; NULL when none. Never written by Scanner.
    quantity_requested_manual: Mapped[int | None] = mapped_column(
        Integer, nullable=True
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
    # NULL only on a draft snapshot nobody typed a value for — it borrows the
    # active version's number on read. Non-null once activated (check below).
    quantity_missing: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    # The version's `active_at`, denormalised; NULL while the version is a draft.
    active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
        # One **active** snapshot per row; a draft's snapshot of the same row sits
        # beside it (2026-09-28: the predicate is the pair, not `closed_at` alone).
        Index(
            "uix_stock_report_item_snapshots_row_active",
            "workspace_id",
            "stock_report_item_id",
            unique=True,
            postgresql_where=text(ACTIVE_SNAPSHOT_WHERE),
        ),
        UniqueConstraint(
            "version_id",
            "stock_report_item_id",
            name="uq_stock_report_item_snapshots_version_row",
        ),
        # An ordering group is `(version_id, priority)` over open snapshots.
        Index(
            "ix_stock_report_item_snapshots_version_priority_order",
            "version_id",
            "priority",
            "priority_order",
            postgresql_where=text(OPEN_SNAPSHOT_WHERE),
        ),
        CheckConstraint(
            "quantity_requested_scanner >= 0",
            name="ck_stock_report_item_snapshots_quantity_requested_scanner_nonneg",
        ),
        CheckConstraint(
            "quantity_requested_manual >= 0",
            name="ck_stock_report_item_snapshots_quantity_requested_manual_nonneg",
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
        # The Scanner column is frozen exactly when the snapshot is activated.
        CheckConstraint(
            "(quantity_requested_scanner IS NULL) = (active_at IS NULL)",
            name="ck_stock_report_item_snapshots_scanner_iff_activated",
        ),
        # An activated snapshot always has its own missing number.
        CheckConstraint(
            "active_at IS NULL OR quantity_missing IS NOT NULL",
            name="ck_stock_report_item_snapshots_missing_set_once_activated",
        ),
        # A draft's snapshot leaves by deletion, never by closing.
        CheckConstraint(
            "closed_at IS NULL OR active_at IS NOT NULL",
            name="ck_stock_report_item_snapshots_closed_implies_activated",
        ),
    )
