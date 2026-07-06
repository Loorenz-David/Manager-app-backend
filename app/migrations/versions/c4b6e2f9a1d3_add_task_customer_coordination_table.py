"""add task_customer_coordinations table

Revision ID: c4b6e2f9a1d3
Revises: aa10c8c7e008
Create Date: 2026-07-04 19:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4b6e2f9a1d3"
down_revision: Union[str, Sequence[str], None] = "aa10c8c7e008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE history_record_entity_type_enum ADD VALUE IF NOT EXISTS 'task_customer_coordination'")

    op.create_table(
        "task_customer_coordinations",
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "pending",
                "coordinating",
                "completed",
                name="task_customer_coordination_state_enum",
                create_type=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(
        "ix_task_customer_coordinations_state", "task_customer_coordinations", ["state"], unique=False
    )
    op.create_index(
        "ix_task_customer_coordinations_task_id", "task_customer_coordinations", ["task_id"], unique=False
    )
    op.create_index(
        "ix_task_customer_coordinations_workspace_id",
        "task_customer_coordinations",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_customer_coordinations_workspace_id", table_name="task_customer_coordinations")
    op.drop_index("ix_task_customer_coordinations_task_id", table_name="task_customer_coordinations")
    op.drop_index("ix_task_customer_coordinations_state", table_name="task_customer_coordinations")
    op.drop_table("task_customer_coordinations")
    op.execute("DROP TYPE IF EXISTS task_customer_coordination_state_enum")
