"""add_task_step_acknowledgments

Revision ID: f1a2b3c4d5e6
Revises: e4a7c9d2b18f
Create Date: 2026-07-15 18:20:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e4a7c9d2b18f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'task_step_acknowledgments',
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('workspace_id', sa.String(length=64), nullable=False),
        sa.Column('step_id', sa.String(length=64), nullable=False),
        sa.Column('task_id', sa.String(length=64), nullable=False),
        sa.Column('worker_id', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.String(length=1024), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.String(length=64), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_id', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['step_id'], ['task_steps.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['worker_id'], ['users.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['deleted_by_id'], ['users.client_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('client_id'),
    )
    op.create_index(
        'ix_task_step_acknowledgments_workspace_id',
        'task_step_acknowledgments', ['workspace_id'],
    )
    op.create_index(
        'ix_task_step_acknowledgments_step_id',
        'task_step_acknowledgments', ['step_id'],
    )
    op.create_index(
        'ix_task_step_acknowledgments_task_id',
        'task_step_acknowledgments', ['task_id'],
    )
    op.create_index(
        'ix_task_step_acknowledgments_worker_id',
        'task_step_acknowledgments', ['worker_id'],
    )
    op.create_index(
        'ix_task_step_acknowledgments_created_by_id',
        'task_step_acknowledgments', ['created_by_id'],
    )
    op.create_index(
        'uix_task_step_ack_step_worker',
        'task_step_acknowledgments', ['workspace_id', 'step_id', 'worker_id'],
        unique=True,
    )
    op.create_index(
        'ix_task_step_ack_pending_by_worker',
        'task_step_acknowledgments', ['workspace_id', 'worker_id'],
        postgresql_where=sa.text('acknowledged_at IS NULL AND is_deleted = false'),
    )


def downgrade() -> None:
    op.drop_index('ix_task_step_ack_pending_by_worker', table_name='task_step_acknowledgments')
    op.drop_index('uix_task_step_ack_step_worker', table_name='task_step_acknowledgments')
    op.drop_index('ix_task_step_acknowledgments_created_by_id', table_name='task_step_acknowledgments')
    op.drop_index('ix_task_step_acknowledgments_worker_id', table_name='task_step_acknowledgments')
    op.drop_index('ix_task_step_acknowledgments_task_id', table_name='task_step_acknowledgments')
    op.drop_index('ix_task_step_acknowledgments_step_id', table_name='task_step_acknowledgments')
    op.drop_index('ix_task_step_acknowledgments_workspace_id', table_name='task_step_acknowledgments')
    op.drop_table('task_step_acknowledgments')
