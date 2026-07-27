from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class AppUpdatePresentationWorkspaceTarget(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "aupwt"
    __tablename__ = "app_update_presentation_workspace_targets"

    presentation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("app_update_presentations.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    presentation: Mapped["AppUpdatePresentation"] = relationship(
        "AppUpdatePresentation", back_populates="workspace_targets", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint(
            "presentation_id",
            "workspace_id",
            name="uq_app_update_workspace_targets_presentation_workspace",
        ),
    )
