"""add task_post_handlings table

Revision ID: 3c4d5e6f7a8b
Revises: 1f6a0c9b3d2e
Create Date: 2026-07-01 16:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, Sequence[str], None] = "1f6a0c9b3d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE history_record_entity_type_enum ADD VALUE IF NOT EXISTS 'task_post_handling'")

    op.create_table(
        "task_post_handlings",
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "pending",
                "filled",
                "completed",
                name="task_post_handling_state_enum",
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
    op.create_index("ix_task_post_handlings_state", "task_post_handlings", ["state"], unique=False)
    op.create_index("ix_task_post_handlings_task_id", "task_post_handlings", ["task_id"], unique=False)
    op.create_index("ix_task_post_handlings_workspace_id", "task_post_handlings", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_post_handlings_workspace_id", table_name="task_post_handlings")
    op.drop_index("ix_task_post_handlings_task_id", table_name="task_post_handlings")
    op.drop_index("ix_task_post_handlings_state", table_name="task_post_handlings")
    op.drop_table("task_post_handlings")
    op.execute("DROP TYPE IF EXISTS task_post_handling_state_enum")
