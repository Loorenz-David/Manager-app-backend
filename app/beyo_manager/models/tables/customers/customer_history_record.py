from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.customers.enums import CustomerHistoryChangeTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class CustomerHistoryRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "chr"
    __tablename__ = "customer_history_records"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    change_type: Mapped[CustomerHistoryChangeTypeEnum] = mapped_column(
        SAEnum(CustomerHistoryChangeTypeEnum, name="customer_history_change_type_enum", create_type=True),
        nullable=False,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_customer_history_records_workspace_customer_occurred",
            "workspace_id",
            "customer_id",
            "occurred_at",
        ),
        Index(
            "ix_customer_history_records_workspace_customer_created",
            "workspace_id",
            "customer_id",
            "created_at",
        ),
    )
