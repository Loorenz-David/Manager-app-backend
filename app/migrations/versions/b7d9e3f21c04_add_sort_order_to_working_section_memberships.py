"""add_sort_order_to_working_section_memberships

Revision ID: b7d9e3f21c04
Revises: f1a2b3c4d5e6
Create Date: 2026-07-15 18:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'b7d9e3f21c04'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add with a server_default so pre-existing rows get a concrete value on rewrite.
    op.add_column(
        'working_section_memberships',
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
    )

    # Backfill a dense 0-based order per (workspace_id, user_id) over active memberships,
    # ordered by assigned_at so the existing assignment sequence is preserved. Removed
    # rows keep sort_order = 0 (irrelevant once removed_at is set).
    op.execute(
        """
        WITH ranked AS (
            SELECT
                client_id,
                ROW_NUMBER() OVER (
                    PARTITION BY workspace_id, user_id
                    ORDER BY assigned_at, client_id
                ) - 1 AS new_order
            FROM working_section_memberships
            WHERE removed_at IS NULL
        )
        UPDATE working_section_memberships AS m
        SET sort_order = ranked.new_order
        FROM ranked
        WHERE m.client_id = ranked.client_id
        """
    )


def downgrade() -> None:
    op.drop_column('working_section_memberships', 'sort_order')
