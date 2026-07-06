"""add task assortment column

Revision ID: 1f6a0c9b3d2e
Revises: 9a8b7c6d5e4f
Create Date: 2026-07-01 15:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f6a0c9b3d2e"
down_revision: Union[str, Sequence[str], None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("assortment", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "assortment")
