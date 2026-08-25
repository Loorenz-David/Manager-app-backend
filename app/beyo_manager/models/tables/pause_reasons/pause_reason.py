from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin, generate_id


class PauseReason(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "par"
    __tablename__ = "pause_reasons"

    def __init__(self, **kwargs):
        client_id = kwargs.get("client_id") or generate_id(self.CLIENT_ID_PREFIX)
        kwargs["client_id"] = client_id
        if kwargs.get("slug") is None:
            kwargs["slug"] = f"custom_{client_id}"
        super().__init__(**kwargs)

    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pause_type: Mapped[PauseTypeEnum] = mapped_column(
        SAEnum(PauseTypeEnum, name="pause_reason_type_enum", create_type=True),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    requires_description: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # `slug` and `is_system_managed` are INERT PUBLISHED CONTRACT, not behaviour.
    #
    # No backend path resolves a pause reason by slug any more — system transitions carry a
    # code-owned `transition_reason` instead, so they no longer depend on a catalog row existing in
    # a workspace. `is_system_managed` is written `False` for every row and guards nothing.
    #
    # Both columns survive because `frontend/packages/pause-reasons/src/types.ts` declares them
    # required and non-nullable (`slug: z.string()`, `is_system_managed: z.boolean()`), so removing
    # either would fail Zod validation on every pause-reasons response — not merely on a branch that
    # reads it. Keep them, keep them serialized, and do not treat either as meaningful.
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    is_system_managed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        Index(
            "uix_pause_reasons_workspace_name_active",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # Scoped to the workspace. This index was GLOBALLY unique, which meant a slug could exist
        # in exactly one workspace database-wide — so bootstrapping a second workspace raised
        # IntegrityError, and only one workspace ever received the default catalog.
        Index("uq_pause_reasons_slug", "workspace_id", "slug", unique=True),
        Index("ix_pause_reasons_workspace_type", "workspace_id", "pause_type"),
    )
