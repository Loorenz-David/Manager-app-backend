from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class PauseReasonUserLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "prul"
    __tablename__ = "pause_reason_user_links"

    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pause_reason_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("pause_reasons.client_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "pause_reason_id",
            "user_id",
            name="uq_pause_reason_user_links_target",
        ),
    )
