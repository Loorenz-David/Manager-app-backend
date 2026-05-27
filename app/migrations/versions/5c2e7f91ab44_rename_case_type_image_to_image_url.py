"""rename case_type image to image_url

Revision ID: 5c2e7f91ab44
Revises: 29c99ef46f70
Create Date: 2026-05-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "5c2e7f91ab44"
down_revision: Union[str, None] = "29c99ef46f70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("case_types", "image", new_column_name="image_url")


def downgrade() -> None:
    op.alter_column("case_types", "image_url", new_column_name="image")