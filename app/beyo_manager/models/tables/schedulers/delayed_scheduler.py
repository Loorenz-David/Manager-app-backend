from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.schedulers.enums import (
    DelayedSchedulerTypeEnum,
    SchedulerOriginSourceEnum,
    SchedulerStateEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class DelayedScheduler(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "dsch"
    __tablename__ = "delayed_schedulers"

    type: Mapped[DelayedSchedulerTypeEnum] = mapped_column(
        SAEnum(DelayedSchedulerTypeEnum, name="delayed_scheduler_type_enum", create_type=True),
        nullable=False,
    )
    state: Mapped[SchedulerStateEnum] = mapped_column(
        SAEnum(SchedulerStateEnum, name="scheduler_state_enum", create_type=True),
        nullable=False,
        default=SchedulerStateEnum.ACTIVE,
        index=True,
    )
    origin_source: Mapped[SchedulerOriginSourceEnum] = mapped_column(
        SAEnum(SchedulerOriginSourceEnum, name="scheduler_origin_source_enum", create_type=True),
        nullable=False,
        default=SchedulerOriginSourceEnum.COMMAND,
    )

    origin_id:        Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_client_id:  Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scheduled_for:    Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    payload_snapshot: Mapped[dict]       = mapped_column(JSON, nullable=False)
    last_error:       Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fired_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
