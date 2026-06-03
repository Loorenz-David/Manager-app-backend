"""add_issue_mode_to_issue_type

Revision ID: 0f7d4c2b1e9a
Revises: c8b2d91e4f77
Create Date: 2026-06-03 16:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0f7d4c2b1e9a"
down_revision: Union[str, None] = "c8b2d91e4f77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_issue_mode_enum = postgresql.ENUM(
    "graded",
    "switch",
    name="issue_mode_enum",
    create_type=False,
)


def upgrade() -> None:
    _issue_mode_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "issue_types",
        sa.Column(
            "issue_mode",
            postgresql.ENUM("graded", "switch", name="issue_mode_enum", create_type=False),
            nullable=True,
        ),
    )
    op.execute("UPDATE issue_types SET issue_mode = 'graded' WHERE issue_mode IS NULL")
    op.alter_column("issue_types", "issue_mode", nullable=False)

    op.add_column(
        "item_issues",
        sa.Column("issue_mode_snapshot", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("item_issues", "issue_mode_snapshot")
    op.drop_column("issue_types", "issue_mode")
    _issue_mode_enum.drop(op.get_bind(), checkfirst=True)
