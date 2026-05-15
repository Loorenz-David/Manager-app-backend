from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserWorkProfile(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uwp"
    __tablename__ = "user_work_profiles"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    salary_per_hour_before_tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    salary_per_hour_after_tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_user_work_profiles_user_workspace"),
        CheckConstraint(
            "salary_per_hour_before_tax IS NULL OR salary_per_hour_before_tax >= 0",
            name="ck_user_work_profiles_salary_before_tax",
        ),
        CheckConstraint(
            "salary_per_hour_after_tax IS NULL OR salary_per_hour_after_tax >= 0",
            name="ck_user_work_profiles_salary_after_tax",
        ),
        Index("ix_user_work_profiles_workspace_user", "workspace_id", "user_id"),
    )
