from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkingSectionDependency(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "wsd"
    __tablename__ = "working_section_dependencies"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dependent_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    prerequisite_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "dependent_section_id",
            "prerequisite_section_id",
            name="uq_working_section_dependencies_unique_edge",
        ),
        CheckConstraint(
            "dependent_section_id != prerequisite_section_id",
            name="ck_working_section_dependencies_no_self_ref",
        ),
    )
