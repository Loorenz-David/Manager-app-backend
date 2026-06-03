"""add_order_list_to_working_sections

Revision ID: 5ad879ec99d9
Revises: f4a1c9d8e2b0
Create Date: 2026-06-02 14:44:03.765435
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '5ad879ec99d9'
down_revision: Union[str, None] = 'f4a1c9d8e2b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('working_sections', sa.Column('order_list', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('working_sections', 'order_list')
