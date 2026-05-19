"""add_username_snapshot_to_history_record

Revision ID: 869a18698f34
Revises: 868a18698f33
Create Date: 2026-05-19 08:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '869a18698f34'
down_revision: Union[str, None] = '868a18698f33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('history_records', sa.Column('username_snapshot', sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column('history_records', 'username_snapshot')
