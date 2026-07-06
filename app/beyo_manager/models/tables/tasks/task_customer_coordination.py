from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class TaskCustomerCoordination(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tcc"
    __tablename__ = "task_customer_coordinations"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[TaskCustomerCoordinationStateEnum] = mapped_column(
        SAEnum(
            TaskCustomerCoordinationStateEnum,
            name="task_customer_coordination_state_enum",
            create_type=True,
        ),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
