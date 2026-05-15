from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class PendingUpload(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "pu"
    __tablename__ = "pending_uploads"

    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", deferrable=True), nullable=False, index=True)
    created_by_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id", deferrable=True), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[PendingUploadStatusEnum] = mapped_column(
        SAEnum(PendingUploadStatusEnum, name="pending_upload_status_enum", create_type=True),
        nullable=False,
        default=PendingUploadStatusEnum.PENDING,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    upload_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", foreign_keys=[workspace_id])
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
