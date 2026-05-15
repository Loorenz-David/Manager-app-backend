"""partial_unique_index_working_sections_name

Revision ID: b9d3e4f12a87
Revises: ec9017a0245c
Create Date: 2026-05-15 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b9d3e4f12a87'
down_revision: Union[str, None] = 'ec9017a0245c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Replace the plain unique constraint with a partial unique index so that
    # soft-deleted sections do not block reuse of their names.
    op.drop_constraint('uq_working_sections_workspace_name', 'working_sections', type_='unique')
    op.execute(
        """
        CREATE UNIQUE INDEX uix_working_sections_name_active
        ON working_sections (workspace_id, name)
        WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    op.drop_index('uix_working_sections_name_active', table_name='working_sections')
    op.create_unique_constraint(
        'uq_working_sections_workspace_name',
        'working_sections',
        ['workspace_id', 'name'],
    )
