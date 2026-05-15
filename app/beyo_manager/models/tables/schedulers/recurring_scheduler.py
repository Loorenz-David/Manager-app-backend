from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.schedulers.enums import (
    RecurringSchedulerIntervalValueEnum,
    RecurringSchedulerTypeEnum,
    SchedulerOriginSourceEnum,
    SchedulerStateEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class RecurringScheduler(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "rsch"
    __tablename__ = "recurring_schedulers"

    type: Mapped[RecurringSchedulerTypeEnum] = mapped_column(
        SAEnum(RecurringSchedulerTypeEnum, name="recurring_scheduler_type_enum", create_type=True),
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

    origin_id:       Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    interval:       Mapped[int]                              = mapped_column(Integer, nullable=False)
    interval_value: Mapped[RecurringSchedulerIntervalValueEnum] = mapped_column(
        SAEnum(
            RecurringSchedulerIntervalValueEnum,
            name="recurring_scheduler_interval_value_enum",
            create_type=True,
        ),
        nullable=False,
    )

    last_interval:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_snapshot: Mapped[dict]            = mapped_column(JSON, nullable=False)
    last_error:       Mapped[str | None]      = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
