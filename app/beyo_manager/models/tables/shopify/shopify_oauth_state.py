from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.shopify.enums import ShopifyOAuthStateStatusEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class ShopifyOAuthState(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "shpoau"
    __tablename__ = "shopify_oauth_states"
    __table_args__ = (
        UniqueConstraint("state", name="uq_shopify_oauth_states_state"),
        Index("ix_shopify_oauth_states_workspace_user", "workspace_id", "user_id"),
        Index("ix_shopify_oauth_states_shop_domain", "shop_domain"),
        Index("ix_shopify_oauth_states_expires_at", "expires_at"),
        Index("ix_shopify_oauth_states_consumed_at", "consumed_at"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shop_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ShopifyOAuthStateStatusEnum] = mapped_column(
        SAEnum(ShopifyOAuthStateStatusEnum, name="shopify_oauth_state_status_enum", create_type=True),
        nullable=False,
        default=ShopifyOAuthStateStatusEnum.PENDING,
        server_default=ShopifyOAuthStateStatusEnum.PENDING.value,
        index=True,
    )
    requested_scopes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    redirect_after_success: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
