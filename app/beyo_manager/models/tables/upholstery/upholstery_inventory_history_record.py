"""Append-only ledger of every upholstery inventory movement.

One row per quantity mutation (written by ``services/commands/upholstery/_inventory_history.py``,
called from the helpers in ``_inventory_mutations.py``) plus child rows for requirement state
changes the movement caused. ``UpholsteryInventory`` quantities are a projection of this ledger:
``after_*`` of the latest row equals the inventory's current totals unless something changed the
totals outside the recorded paths (the read side reports that as drift).

Rows are immutable once committed. No soft delete, no ``updated_*``.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import InventoryMovementTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


# Ledger bucket name → UpholsteryInventory column. The single source for snapshot mapping.
INVENTORY_BUCKET_COLUMNS: dict[str, str] = {
    "stored": "current_stored_amount_meters",
    "in_use": "current_amount_in_use_meters",
    "in_need": "current_amount_in_need_meters",
    "ordered": "current_amount_ordered_meters",
    "total_used": "total_upholstery_used_meters",
    "total_used_inventory": "total_upholstery_used_inventory_meters",
    "total_used_surplus": "total_upholstery_used_surplus_meters",
    "total_surplus": "total_upholstery_surplus_meters",
}
INVENTORY_BUCKETS: tuple[str, ...] = tuple(INVENTORY_BUCKET_COLUMNS)


def _qty() -> Mapped[Decimal | None]:
    return mapped_column(Numeric(14, 3), nullable=True)


class UpholsteryInventoryHistoryRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uih"
    __tablename__ = "upholstery_inventory_history_records"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_inventory_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("upholstery_inventory.client_id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[InventoryMovementTypeEnum] = mapped_column(
        SAEnum(
            InventoryMovementTypeEnum,
            name="upholstery_inventory_movement_type_enum",
            create_type=True,
        ),
        nullable=False,
    )
    # InventoryMovementTriggerEnum value, stored as a string on purpose (no ALTER TYPE for new origins).
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    # One id per outermost service run; groups everything a single command wrote.
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Requirement-state children point at the movement that caused them.
    parent_record_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("upholstery_inventory_history_records.client_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Chain pointer: the inventory's latest_projection_history_id when this row was written.
    previous_record_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("upholstery_inventory_history_records.client_id", ondelete="RESTRICT"),
        nullable=True,
    )

    # The helper's input quantity: magnitude, a signed delta for need adjustments,
    # or the new absolute value for a stored-amount set.
    quantity_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)

    before_stored_meters: Mapped[Decimal | None] = _qty()
    before_in_use_meters: Mapped[Decimal | None] = _qty()
    before_in_need_meters: Mapped[Decimal | None] = _qty()
    before_ordered_meters: Mapped[Decimal | None] = _qty()
    before_total_used_meters: Mapped[Decimal | None] = _qty()
    before_total_used_inventory_meters: Mapped[Decimal | None] = _qty()
    before_total_used_surplus_meters: Mapped[Decimal | None] = _qty()
    before_total_surplus_meters: Mapped[Decimal | None] = _qty()
    after_stored_meters: Mapped[Decimal | None] = _qty()
    after_in_use_meters: Mapped[Decimal | None] = _qty()
    after_in_need_meters: Mapped[Decimal | None] = _qty()
    after_ordered_meters: Mapped[Decimal | None] = _qty()
    after_total_used_meters: Mapped[Decimal | None] = _qty()
    after_total_used_inventory_meters: Mapped[Decimal | None] = _qty()
    after_total_used_surplus_meters: Mapped[Decimal | None] = _qty()
    after_total_surplus_meters: Mapped[Decimal | None] = _qty()

    # Soft references (no FK): the requirement row may be inserted after the ledger row,
    # and the ledger must outlive deletes of what it references.
    requirement_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    item_upholstery_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    task_step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upholstery_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    requirement_from_state: Mapped[ItemUpholsteryRequirementStateEnum | None] = mapped_column(
        SAEnum(
            ItemUpholsteryRequirementStateEnum,
            name="item_upholstery_requirement_state_enum",
            create_type=False,
        ),
        nullable=True,
    )
    requirement_to_state: Mapped[ItemUpholsteryRequirementStateEnum | None] = mapped_column(
        SAEnum(
            ItemUpholsteryRequirementStateEnum,
            name="item_upholstery_requirement_state_enum",
            create_type=False,
        ),
        nullable=True,
    )

    anomaly: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_reconstructed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # Idempotency key for migration baselines / backfilled rows.
    reconstruction_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index(
            "ix_uih_inventory_toplevel_created",
            "upholstery_inventory_id",
            text("created_at DESC"),
            text("client_id DESC"),
            postgresql_where=text("parent_record_id IS NULL"),
        ),
        Index(
            "uix_uih_reconstruction_key",
            "reconstruction_key",
            unique=True,
            postgresql_where=text("reconstruction_key IS NOT NULL"),
        ),
    )
