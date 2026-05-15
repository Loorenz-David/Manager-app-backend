from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class AuditLog(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "aud"
    __tablename__ = "audit_logs"

    # What happened
    event: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Who did it
    actor_user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=True, index=True
    )
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Workspace scope
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True
    )

    # Affected resource
    resource_type:      Mapped[str | None] = mapped_column(String(64),  nullable=True)
    resource_client_id: Mapped[str | None] = mapped_column(String(64),  nullable=True)

    # Structured context
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Request metadata
    ip_address:  Mapped[str | None] = mapped_column(String(64),  nullable=True)
    user_agent:  Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id:  Mapped[str | None] = mapped_column(String(64),  nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc),
    )
