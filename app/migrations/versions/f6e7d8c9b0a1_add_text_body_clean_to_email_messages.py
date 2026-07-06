"""add_text_body_clean_to_email_messages

Revision ID: f6e7d8c9b0a1
Revises: dd861a418d9d, e1b2c3d4f5a6
Create Date: 2026-07-06 11:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f6e7d8c9b0a1"
down_revision: Union[str, Sequence[str], None] = ("dd861a418d9d", "e1b2c3d4f5a6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("email_messages", sa.Column("text_body_clean", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("email_messages", "text_body_clean")
