"""add_image_url_to_item_categories

Revision ID: 1a2b3c4d5e6f
Revises: 4c1d9c2e5a11
Create Date: 2026-05-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "4c1d9c2e5a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("item_categories", sa.Column("image_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("item_categories", "image_url")
