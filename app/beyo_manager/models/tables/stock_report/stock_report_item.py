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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class StockReportItem(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "sri"
    __tablename__ = "stock_report_items"
    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    item_category_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("item_categories.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False)
    properties_signature: Mapped[str] = mapped_column(String(64), nullable=False)
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
            "uix_stock_report_items_identity_active",
            "workspace_id",
            "item_category_id",
            "properties_signature",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "ix_stock_report_items_workspace_priority_order",
            "workspace_id",
            "priority",
            "priority_order",
        ),
        CheckConstraint(
            "quantity_requested >= 0",
            name="ck_stock_report_items_quantity_requested_nonneg",
        ),
        CheckConstraint(
            "quantity_awaiting >= 0",
            name="ck_stock_report_items_quantity_awaiting_nonneg",
        ),
        CheckConstraint(
            "quantity_in_queue >= 0",
            name="ck_stock_report_items_quantity_in_queue_nonneg",
        ),
        CheckConstraint(
            "quantity_in_progress >= 0",
            name="ck_stock_report_items_quantity_in_progress_nonneg",
        ),
    )
