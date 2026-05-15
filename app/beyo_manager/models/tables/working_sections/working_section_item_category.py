from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkingSectionItemCategory(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "wsic"
    __tablename__ = "working_section_item_categories"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_category_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("item_categories.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "working_section_id",
            "item_category_id",
            name="uq_ws_item_categories_unique",
        ),
    )
