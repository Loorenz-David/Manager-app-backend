import enum
from datetime import datetime, timezone
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from beyo_manager.domain.base.enums import EventStateEnum


class Event:
    """Lifecycle mixin for concrete domain operation event tables (42_event.md).
    Always combine with IdentityMixin and Base:
      class MyEvent(IdentityMixin, Event, Base): ...
    Set EVENT_TYPE_ENUM and EVENT_ERROR_ENUM on every concrete subclass.
    """

    EVENT_TYPE_ENUM:  ClassVar[type[enum.Enum]]
    EVENT_ERROR_ENUM: ClassVar[type[enum.Enum]]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Only enforce on SQLAlchemy model classes (have __tablename__)
        if hasattr(cls, "__tablename__"):
            for attr in ("EVENT_TYPE_ENUM", "EVENT_ERROR_ENUM"):
                if not hasattr(cls, attr):
                    raise AttributeError(
                        f"Concrete event model {cls.__name__} must define {attr}."
                    )

    @declared_attr
    def created_by_id(cls) -> Mapped[str]:
        return mapped_column(
            String(64), ForeignKey("users.client_id", deferrable=True),
            nullable=False, index=True,
        )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    state: Mapped[EventStateEnum] = mapped_column(
        SAEnum(EventStateEnum, name="event_record_state_enum", create_type=True),
        nullable=False,
        default=EventStateEnum.REQUESTED,
        index=True,
    )

    @declared_attr
    def type(cls) -> Mapped[enum.Enum]:
        return mapped_column(
            SAEnum(cls.EVENT_TYPE_ENUM, name=f"{cls.__tablename__}_type_enum", create_type=True),
            nullable=False,
        )

    @declared_attr
    def last_error(cls) -> Mapped[enum.Enum | None]:
        return mapped_column(
            SAEnum(cls.EVENT_ERROR_ENUM, name=f"{cls.__tablename__}_error_enum", create_type=True),
            nullable=True,
        )

    attempts:     Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int]        = mapped_column(Integer, nullable=False, default=3)
    description:  Mapped[str | None] = mapped_column(String(512), nullable=True)
