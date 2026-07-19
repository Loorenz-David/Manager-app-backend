"""seed_auto_clock_out_open_shifts_scheduler

Revision ID: b4074f2e26c4
Revises: 759ed2d573c2
Create Date: 2026-07-20 01:39:02.384026
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b4074f2e26c4"
down_revision: Union[str, None] = "759ed2d573c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO recurring_schedulers (
            client_id,
            type,
            state,
            origin_source,
            origin_id,
            event_client_id,
            interval,
            interval_value,
            last_interval,
            payload_snapshot,
            last_error,
            created_at
        ) VALUES (
            'rsch_01KXY000000000000000000000',
            'auto_clock_out_open_shifts',
            'active',
            'worker',
            NULL,
            NULL,
            1,
            'days',
            NULL,
            '{}'::json,
            NULL,
            date_trunc('day', CURRENT_TIMESTAMP)
        )
        ON CONFLICT (client_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM recurring_schedulers "
        "WHERE client_id = 'rsch_01KXY000000000000000000000'"
    )
