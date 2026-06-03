"""add_pause_case_created_to_step_event_reason_enum

Revision ID: b7c4e1d2a9f0
Revises: 5ad879ec99d9
Create Date: 2026-06-02 16:10:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b7c4e1d2a9f0"
down_revision: Union[str, None] = "5ad879ec99d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'step_event_reason_enum'
                  AND e.enumlabel = 'pause_case_created'
            ) THEN
                ALTER TYPE step_event_reason_enum ADD VALUE 'pause_case_created';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    pass
