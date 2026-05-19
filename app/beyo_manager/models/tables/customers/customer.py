from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.customers.enums import CustomerStatusEnum, CustomerTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class Customer(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "cus"
    __tablename__ = "customers"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_type: Mapped[CustomerTypeEnum] = mapped_column(
        SAEnum(CustomerTypeEnum, name="customer_type_enum", create_type=True),
        nullable=False,
        default=CustomerTypeEnum.UNKNOWN,
        index=True,
    )
    status: Mapped[CustomerStatusEnum] = mapped_column(
        SAEnum(CustomerStatusEnum, name="customer_status_enum", create_type=True),
        nullable=False,
        default=CustomerStatusEnum.ACTIVE,
        index=True,
    )
    primary_phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_phone_number_normalized: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    primary_email_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_customers_workspace_display_name", "workspace_id", "display_name"),
        Index("ix_customers_workspace_phone", "workspace_id", "primary_phone_number"),
        Index("ix_customers_workspace_email", "workspace_id", "primary_email"),
        Index(
            "ix_customers_workspace_phone_normalized",
            "workspace_id",
            "primary_phone_number_normalized",
        ),
        Index("ix_customers_workspace_email_normalized", "workspace_id", "primary_email_normalized"),
    )
