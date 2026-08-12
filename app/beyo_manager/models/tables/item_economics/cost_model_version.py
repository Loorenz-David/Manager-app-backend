from datetime import date, datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class CostModelVersion(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "cmv"
    __tablename__ = "cost_model_versions"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[ItemCurrencyEnum] = mapped_column(SAEnum(ItemCurrencyEnum, name="cost_model_version_currency_enum", create_type=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    updated_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from", name="ck_cost_model_versions_effective_window"),
        Index("uix_cost_model_versions_open", "workspace_id", unique=True, postgresql_where=text("effective_to IS NULL AND is_deleted = false")),
    )
