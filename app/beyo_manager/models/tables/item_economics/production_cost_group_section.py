from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class ProductionCostGroupSection(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "pcgs"
    __tablename__ = "production_cost_group_sections"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    production_cost_group_id: Mapped[str] = mapped_column(String(64), ForeignKey("production_cost_groups.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    working_section_id: Mapped[str] = mapped_column(String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    added_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (Index("uix_production_cost_group_sections_active", "workspace_id", "working_section_id", unique=True, postgresql_where=text("removed_at IS NULL")),)
