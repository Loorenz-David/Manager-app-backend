"""`stock_report_snapshot_versions` — a board version: a draft, the active one, or
a closed one.

The state is **derived, never stored** (`snapshot_rules.version_state`):

| state    | `active_at` | `closed_at` |
|----------|-------------|-------------|
| `draft`  | NULL        | NULL        |
| `active` | set         | NULL        |
| `closed` | set         | set         |

`active_at NULL, closed_at set` is unstorable (`ck_…_closed_implies_activated`).
A workspace holds **many drafts** and at most one active version
(`uix_stock_report_snapshot_versions_active`, predicate on the pair). A draft is
live — its rows' requested quantities and its row set follow the stock report — and
holds of its own only priorities, typed missing counts and manual requested values.
Activation (by hand, or on `scheduled_activation_at` through the delayed
scheduler) closes the active version and freezes Scanner's values into the draft's
snapshots. Drafts are hard-deleted; activated versions are closed, never deleted —
closing is their lifecycle, and a closed version is immutable history that
`apply_stock_report_snapshot_version_priorities` can copy from.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin

ACTIVE_VERSION_WHERE = "active_at IS NOT NULL AND closed_at IS NULL"


class StockReportSnapshotVersion(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "srv"
    __tablename__ = "stock_report_snapshot_versions"
    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # The user's note; editable in any state. Stripped; empty → NULL.
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # When the version went live (the fire time for a scheduled activation, not
    # the scheduled time). NULL while a draft.
    active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # A draft's pending self-activation, stored in UTC; NULL = no schedule. The
    # delayed-scheduler row is the mechanism, this column is the truth.
    scheduled_activation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # What a **scheduled** activation does with the rows the draft typed no
    # missing for: keep the active version's value (true) or reset to 0 (false).
    # Read from this column at fire time; a manual activation uses its body.
    scheduled_activation_keeps_active_missing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    snapshot_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
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
    closed_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    __table_args__ = (
        # "One active version per workspace" is a database fact, not a code promise.
        Index(
            "uix_stock_report_snapshot_versions_active",
            "workspace_id",
            unique=True,
            postgresql_where=text(ACTIVE_VERSION_WHERE),
        ),
        Index(
            "ix_stock_report_snapshot_versions_workspace_active_at",
            "workspace_id",
            "active_at",
        ),
        Index(
            "ix_stock_report_snapshot_versions_workspace_created_at",
            "workspace_id",
            "created_at",
        ),
        CheckConstraint(
            "closed_at IS NULL OR active_at IS NOT NULL",
            name="ck_stock_report_snapshot_versions_closed_implies_activated",
        ),
        CheckConstraint(
            "scheduled_activation_at IS NULL OR active_at IS NULL",
            name="ck_stock_report_snapshot_versions_schedule_only_on_draft",
        ),
    )
