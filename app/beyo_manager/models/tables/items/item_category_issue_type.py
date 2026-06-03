from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class ItemCategoryIssueType(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "icit"
    __tablename__ = "item_category_issue_types"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_category_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("item_categories.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issue_type_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("issue_types.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    placement_of_issue: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "item_category_id",
            "issue_type_id",
            "placement_of_issue",
            name="uq_item_category_issue_types_unique",
        ),
    )
