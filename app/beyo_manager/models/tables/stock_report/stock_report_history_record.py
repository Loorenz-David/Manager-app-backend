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
)
from sqlalchemy.orm import Mapped, mapped_column
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportPriorityEnum,
    StockReportQuantityRequestedSourceEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class StockReportHistoryRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "srh"
    __tablename__ = "stock_report_history_records"
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
    type: Mapped[StockReportHistoryRecordTypeEnum] = mapped_column(
        SAEnum(
            StockReportHistoryRecordTypeEnum,
            name="stock_report_history_record_type_enum",
            create_type=True,
        ),
        nullable=False,
        index=True,
    )
    quantity_requested: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Where `quantity_requested` came from (draft versions, 2026-09-28): Scanner's
    # value, or a user's manual override on the snapshot the record was written
    # against. Scanner's own `quantity_requested_change` records are always `scanner`.
    quantity_requested_source: Mapped[StockReportQuantityRequestedSourceEnum] = (
        mapped_column(
            SAEnum(
                StockReportQuantityRequestedSourceEnum,
                name="stock_report_quantity_requested_source_enum",
                create_type=True,
            ),
            nullable=False,
            default=StockReportQuantityRequestedSourceEnum.SCANNER,
            server_default="scanner",
        )
    )
    quantity_awaiting: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    priority: Mapped[StockReportPriorityEnum | None] = mapped_column(
        SAEnum(
            StockReportPriorityEnum, name="stock_report_priority_enum", create_type=True
        ),
        nullable=True,
    )
    priority_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
            "ix_stock_report_history_records_row_type_created",
            "stock_report_item_id",
            "type",
            "created_at",
        ),
        CheckConstraint(
            "quantity_awaiting >= 0",
            name="ck_stock_report_history_records_quantity_awaiting_nonneg",
        ),
    )
