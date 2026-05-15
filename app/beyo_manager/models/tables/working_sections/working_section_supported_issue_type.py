from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkingSectionSupportedIssueType(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "wsit"
    __tablename__ = "working_section_supported_issue_types"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issue_type_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("issue_types.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "working_section_id",
            "issue_type_id",
            name="uq_ws_supported_issue_types_unique",
        ),
    )
