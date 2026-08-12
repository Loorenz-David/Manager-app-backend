from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)


class ItemValuation(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ival"
    __tablename__ = "item_valuations"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), ForeignKey("items.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    expected_sale_price_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchase_cost_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[ItemCurrencyEnum] = mapped_column(SAEnum(ItemCurrencyEnum, name="item_valuation_currency_enum", create_type=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("item_valuations.client_id", use_alter=True, name="fk_item_valuations_superseded_by_id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (
        CheckConstraint("expected_sale_price_minor IS NULL OR expected_sale_price_minor >= 0", name="ck_item_valuations_expected_sale_price_minor_non_negative"),
        CheckConstraint("purchase_cost_minor IS NULL OR purchase_cost_minor >= 0", name="ck_item_valuations_purchase_cost_minor_non_negative"),
        CheckConstraint("expected_sale_price_minor IS NOT NULL OR purchase_cost_minor IS NOT NULL", name="ck_item_valuations_amount_present"),
        Index("uix_item_valuations_current", "item_id", unique=True, postgresql_where=text("superseded_at IS NULL AND is_deleted = false")),
    )
