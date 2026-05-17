from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class Item(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "itm"
    __tablename__ = "items"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    article_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    state: Mapped[ItemStateEnum] = mapped_column(
        SAEnum(ItemStateEnum, name="item_state_enum", create_type=True),
        nullable=False,
        default=ItemStateEnum.PENDING,
        index=True,
    )
    item_category_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("item_categories.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    designer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    height_in_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width_in_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    depth_in_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_value_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_cost_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_currency: Mapped[ItemCurrencyEnum | None] = mapped_column(
        SAEnum(ItemCurrencyEnum, name="item_currency_enum", create_type=True), nullable=True
    )
    item_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    item_category_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    item_major_category_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
        Index("ix_items_workspace_state", "workspace_id", "state"),
        Index(
            "uix_items_workspace_article_number",
            "workspace_id",
            "article_number",
            unique=True,
            postgresql_where=text("article_number IS NOT NULL AND is_deleted = false"),
        ),
        Index(
            "uix_items_workspace_sku",
            "workspace_id",
            "sku",
            unique=True,
            postgresql_where=text("sku IS NOT NULL AND is_deleted = false"),
        ),
    )
