"""add_major_category_to_production_cost_groups

Revision ID: 5caae620088c
Revises: 90cdd23a828e
Create Date: 2026-08-13 12:56:37.447551
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '5caae620088c'
down_revision: Union[str, None] = '90cdd23a828e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_item_major_category_enum = postgresql.ENUM(
    "wood", "seat", name="item_major_category_enum", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    group_ids = list(
        bind.execute(
            sa.text("SELECT client_id FROM production_cost_groups ORDER BY client_id")
        ).scalars()
    )
    if group_ids:
        dependent_counts = {
            table: bind.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in (
                "production_cost_group_sections",
                "production_cost_basis_versions",
                "item_cost_evaluations",
            )
        }
        raise RuntimeError(
            "major_category migration refused: "
            f"{len(group_ids)} uncategorizable production_cost_groups; "
            f"client_ids={group_ids}; dependent_counts={dependent_counts}; "
            "delete or otherwise repair the reported rows and re-run"
        )

    op.add_column(
        "production_cost_groups",
        sa.Column("major_category", _item_major_category_enum, nullable=False),
    )
    op.create_index(
        "uix_production_cost_groups_major_category_active",
        "production_cost_groups",
        ["workspace_id", "major_category"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index(
        "uix_production_cost_groups_major_category_active",
        table_name="production_cost_groups",
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_column("production_cost_groups", "major_category")
