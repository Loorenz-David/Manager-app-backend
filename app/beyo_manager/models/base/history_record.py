from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class HistoryRecord:
    """Mixin for history/audit tables. Captures what changed, when, by whom, and why.

    Always combine with IdentityMixin:
        class MyHistoryRecord(IdentityMixin, HistoryRecord, Base): ...
    """

    @declared_attr
    def updated_by_id(cls) -> Mapped[str]:
        return mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    from_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    to_value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
