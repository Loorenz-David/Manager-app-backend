from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.execution.enums import EventTaskOriginSourceEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class ExecutionPayload(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "epl"
    __tablename__ = "execution_payloads"

    origin_source: Mapped[EventTaskOriginSourceEnum] = mapped_column(
        SAEnum(EventTaskOriginSourceEnum, name="event_task_origin_source_enum", create_type=True),
        nullable=False,
    )
    origin_id:        Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_client_id:  Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload:          Mapped[dict]       = mapped_column(JSON, nullable=False)

    execution_task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("execution_tasks.client_id"), nullable=False, unique=True
    )
    execution_task: Mapped["ExecutionTask"] = relationship(
        "ExecutionTask", back_populates="payload"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
