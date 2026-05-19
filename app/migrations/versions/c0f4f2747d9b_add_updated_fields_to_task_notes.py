"""add_updated_fields_to_task_notes

Revision ID: c0f4f2747d9b
Revises: 3a5532f8f0a7
Create Date: 2026-05-18 14:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c0f4f2747d9b'
down_revision: Union[str, None] = '3a5532f8f0a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('task_notes', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('task_notes', sa.Column('updated_by_id', sa.String(length=64), nullable=True))
    op.create_foreign_key(
        'fk_task_notes_updated_by_id',
        'task_notes',
        'users',
        ['updated_by_id'],
        ['client_id'],
        ondelete='RESTRICT',
    )


def downgrade() -> None:
    op.drop_constraint('fk_task_notes_updated_by_id', 'task_notes', type_='foreignkey')
    op.drop_column('task_notes', 'updated_by_id')
    op.drop_column('task_notes', 'updated_at')
