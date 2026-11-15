"""create_upholstery_inventory_history_records

Introduces the append-only upholstery inventory ledger that
`models/tables/upholstery/README.md` deferred: every quantity mutation of an
`upholstery_inventory` row appends one `upholstery_inventory_history_records`
row (with before/after snapshots of the eight quantity buckets), and
requirement state changes caused by a movement are appended as child rows.
`upholstery_inventory.latest_projection_history_id` (never written until now)
gets its FK and points at the newest ledger row.

Data step: one `opening_balance` row per non-deleted inventory, carrying the
current totals as its `after_*` snapshot. It anchors the chain so that every
later movement can be checked against it; history before this migration is
only available as reconstructed rows (scripts/backfill/
backfill_upholstery_inventory_history.py). Idempotent via
`reconstruction_key = 'baseline:<inventory id>'`.

Hand-written.

Revision ID: d7e2a9c4b1f6
Revises: 8c4e1f2a6b93
Create Date: 2026-11-15 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from beyo_manager.models.base.identity import generate_id


revision: str = "d7e2a9c4b1f6"
down_revision: Union[str, Sequence[str], None] = "8c4e1f2a6b93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "upholstery_inventory_history_records"
MOVEMENT_ENUM = "upholstery_inventory_movement_type_enum"
MOVEMENT_VALUES = (
    "opening_balance",
    "inventory_created",
    "need_added",
    "need_adjusted",
    "reserved_for_use",
    "use_finished",
    "used_direct",
    "use_rolled_back",
    "order_placed",
    "order_received",
    "surplus_added",
    "stored_set",
    "allocation_run",
    "requirement_state_changed",
)
BUCKETS = (
    ("stored", "current_stored_amount_meters"),
    ("in_use", "current_amount_in_use_meters"),
    ("in_need", "current_amount_in_need_meters"),
    ("ordered", "current_amount_ordered_meters"),
    ("total_used", "total_upholstery_used_meters"),
    ("total_used_inventory", "total_upholstery_used_inventory_meters"),
    ("total_used_surplus", "total_upholstery_used_surplus_meters"),
    ("total_surplus", "total_upholstery_surplus_meters"),
)
POINTER_FK = "fk_upholstery_inventory_latest_projection_history"


def upgrade() -> None:
    movement_enum = postgresql.ENUM(*MOVEMENT_VALUES, name=MOVEMENT_ENUM)
    movement_enum.create(op.get_bind(), checkfirst=True)
    requirement_state = postgresql.ENUM(name="item_upholstery_requirement_state_enum", create_type=False)

    qty_columns = [
        sa.Column(f"{phase}_{bucket}_meters", sa.Numeric(14, 3), nullable=True)
        for phase in ("before", "after")
        for bucket, _ in BUCKETS
    ]

    op.create_table(
        TABLE,
        sa.Column("client_id", sa.String(64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(64),
            sa.ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "upholstery_inventory_id",
            sa.String(64),
            sa.ForeignKey("upholstery_inventory.client_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("movement_type", postgresql.ENUM(name=MOVEMENT_ENUM, create_type=False), nullable=False),
        sa.Column("trigger", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column(
            "parent_record_id",
            sa.String(64),
            sa.ForeignKey(f"{TABLE}.client_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "previous_record_id",
            sa.String(64),
            sa.ForeignKey(f"{TABLE}.client_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("quantity_meters", sa.Numeric(14, 3), nullable=True),
        *qty_columns,
        sa.Column("requirement_id", sa.String(64), nullable=True),
        sa.Column("item_upholstery_id", sa.String(64), nullable=True),
        sa.Column("item_id", sa.String(64), nullable=True),
        sa.Column("task_id", sa.String(64), nullable=True),
        sa.Column("task_step_id", sa.String(64), nullable=True),
        sa.Column("upholstery_order_id", sa.String(64), nullable=True),
        sa.Column("requirement_from_state", requirement_state, nullable=True),
        sa.Column("requirement_to_state", requirement_state, nullable=True),
        sa.Column("anomaly", sa.String(64), nullable=True),
        sa.Column("note", sa.String(512), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by_id",
            sa.String(64),
            sa.ForeignKey("users.client_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("username_snapshot", sa.String(128), nullable=True),
        sa.Column("is_reconstructed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reconstruction_key", sa.String(128), nullable=True),
    )

    op.create_index(f"ix_{TABLE}_workspace_id", TABLE, ["workspace_id"])
    op.create_index(f"ix_{TABLE}_correlation_id", TABLE, ["correlation_id"])
    op.create_index(f"ix_{TABLE}_parent_record_id", TABLE, ["parent_record_id"])
    op.create_index(f"ix_{TABLE}_requirement_id", TABLE, ["requirement_id"])
    op.create_index(f"ix_{TABLE}_task_id", TABLE, ["task_id"])
    op.create_index(
        "ix_uih_inventory_toplevel_created",
        TABLE,
        ["upholstery_inventory_id", sa.text("created_at DESC"), sa.text("client_id DESC")],
        postgresql_where=sa.text("parent_record_id IS NULL"),
    )
    op.create_index(
        "uix_uih_reconstruction_key",
        TABLE,
        ["reconstruction_key"],
        unique=True,
        postgresql_where=sa.text("reconstruction_key IS NOT NULL"),
    )

    # The pointer column existed but was never written; clear anything stray before the FK.
    op.execute(
        "UPDATE upholstery_inventory SET latest_projection_history_id = NULL "
        "WHERE latest_projection_history_id IS NOT NULL"
    )
    op.create_foreign_key(
        POINTER_FK,
        "upholstery_inventory",
        TABLE,
        ["latest_projection_history_id"],
        ["client_id"],
        ondelete="SET NULL",
        deferrable=True,
        initially="DEFERRED",
    )

    _write_opening_balances()


def _write_opening_balances() -> None:
    bind = op.get_bind()
    inventories = bind.execute(
        sa.text(
            "SELECT client_id FROM upholstery_inventory "
            "WHERE is_deleted = false ORDER BY client_id"
        )
    ).fetchall()

    after_cols = ", ".join(f"after_{bucket}_meters" for bucket, _ in BUCKETS)
    after_vals = ", ".join(f"COALESCE(inv.{column}, 0)" for _, column in BUCKETS)
    insert = sa.text(
        f"""
        INSERT INTO {TABLE} (
            client_id, workspace_id, upholstery_inventory_id, movement_type, trigger,
            {after_cols}, created_at, is_reconstructed, reconstruction_key
        )
        SELECT :record_id, inv.workspace_id, inv.client_id, 'opening_balance', 'migration_baseline',
               {after_vals}, now(), false, :reconstruction_key
        FROM upholstery_inventory inv
        WHERE inv.client_id = :inventory_id
        ON CONFLICT (reconstruction_key) WHERE reconstruction_key IS NOT NULL DO NOTHING
        """
    )
    set_pointer = sa.text(
        f"""
        UPDATE upholstery_inventory inv
        SET latest_projection_history_id = rec.client_id
        FROM {TABLE} rec
        WHERE rec.reconstruction_key = :reconstruction_key
          AND inv.client_id = :inventory_id
        """
    )
    for (inventory_id,) in inventories:
        key = f"baseline:{inventory_id}"
        params = {
            "record_id": generate_id("uih"),
            "inventory_id": inventory_id,
            "reconstruction_key": key,
        }
        bind.execute(insert, params)
        bind.execute(set_pointer, {"reconstruction_key": key, "inventory_id": inventory_id})


def downgrade() -> None:
    op.drop_constraint(POINTER_FK, "upholstery_inventory", type_="foreignkey")
    op.execute("UPDATE upholstery_inventory SET latest_projection_history_id = NULL")
    op.drop_index("uix_uih_reconstruction_key", table_name=TABLE)
    op.drop_index("ix_uih_inventory_toplevel_created", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_task_id", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_requirement_id", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_parent_record_id", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_correlation_id", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_workspace_id", table_name=TABLE)
    op.drop_table(TABLE)
    postgresql.ENUM(name=MOVEMENT_ENUM).drop(op.get_bind(), checkfirst=True)
