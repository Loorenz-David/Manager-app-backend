"""remove_step_event_reason_enum

Revision ID: b58cdffb5ccc
Revises: fb10ac7fd439
Create Date: 2026-07-22 13:31:16.566827
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b58cdffb5ccc'
down_revision: Union[str, None] = 'fb10ac7fd439'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY_STEP_EVENT_REASON = postgresql.ENUM(
    'waiting_for_upholstery',
    'pause_lunch_break',
    'pause_coffee_break',
    'pause_ended_shift',
    'pause_meeting',
    'pause_other_task_priority',
    'pause_case_created',
    name='step_event_reason_enum',
    create_type=False,
)


def upgrade() -> None:
    op.drop_index('ix_step_state_records_reason', table_name='step_state_records')
    op.drop_column('step_state_records', 'reason')
    _LEGACY_STEP_EVENT_REASON.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    _LEGACY_STEP_EVENT_REASON.create(op.get_bind(), checkfirst=True)
    op.add_column('step_state_records', sa.Column('reason', _LEGACY_STEP_EVENT_REASON, nullable=True))
    op.create_index('ix_step_state_records_reason', 'step_state_records', ['reason'], unique=False)
