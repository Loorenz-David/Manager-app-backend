from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from beyo_manager.domain.stock_report.enums import StockReportRepairTargetKindEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class StockReportRepairRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "srr"
    __tablename__ = "stock_report_repair_records"
    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_kind: Mapped[StockReportRepairTargetKindEnum] = mapped_column(
        SAEnum(
            StockReportRepairTargetKindEnum,
            name="stock_report_repair_target_kind_enum",
            create_type=True,
        ),
        nullable=False,
        index=True,
    )
    target_client_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    stored_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    recomputed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    __table_args__ = (
        Index("ix_stock_report_repair_records_target_client_id", "target_client_id"),
    )
