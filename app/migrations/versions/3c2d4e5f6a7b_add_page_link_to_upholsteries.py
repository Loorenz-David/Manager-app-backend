"""add_page_link_to_upholsteries

Revision ID: 3c2d4e5f6a7b
Revises: 6f4d2c1b9a7e, d1e2f3a4b5c6
Create Date: 2026-06-29 17:05:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "3c2d4e5f6a7b"
down_revision: Union[str, Sequence[str], None] = ("6f4d2c1b9a7e", "d1e2f3a4b5c6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("upholsteries", sa.Column("page_link", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("upholsteries", "page_link")
