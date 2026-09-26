"""`stock_report_snapshot_versions` — one board "version" per workspace at a time.

A version is the unit a manager opens (`create_stock_report_snapshot_version`): it
freezes `quantity_requested` of every live row into one `stock_report_item_snapshots`
row and closes the previous version in the same transaction. Versions have no soft
delete — closing **is** their lifecycle, and a closed version is immutable history that
`apply_stock_report_snapshot_version_priorities` can copy from.
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class StockReportSnapshotVersion(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "srv"
    __tablename__ = "stock_report_snapshot_versions"
    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Equal to `created_at` in v1; kept as its own column so a future scheduled
    # activation does not need a schema change.
    active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
            postgresql_where=text("closed_at IS NULL"),
        ),
        Index(
            "ix_stock_report_snapshot_versions_workspace_active_at",
            "workspace_id",
            "active_at",
        ),
    )
