"""create sku_templates table

Revision ID: 261971b16234
Revises: c4e8a1d92f07
Create Date: 2026-07-23 10:01:01.976199
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '261971b16234'
down_revision: Union[str, None] = 'c4e8a1d92f07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sku_templates',
    sa.Column('workspace_id', sa.String(length=64), nullable=False),
    sa.Column(
        'task_type',
        postgresql.ENUM(
            'return', 'pre_order', 'internal',
            name='business_task_type_enum',
            create_type=False,
        ),
        nullable=False,
    ),
    sa.Column('prefix', sa.String(length=32), nullable=False),
    sa.Column('separator', sa.String(length=8), nullable=False),
    sa.Column('pad_width', sa.Integer(), nullable=False),
    sa.Column('last_scalar', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by_id', sa.String(length=64), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_by_id', sa.String(length=64), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_id', sa.String(length=64), nullable=True),
    sa.Column('client_id', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.client_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['deleted_by_id'], ['users.client_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.client_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.client_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('client_id')
    )
    op.create_index(op.f('ix_sku_templates_created_by_id'), 'sku_templates', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_sku_templates_workspace_id'), 'sku_templates', ['workspace_id'], unique=False)
    op.create_index(
        'uix_sku_templates_workspace_task_type',
        'sku_templates',
        ['workspace_id', 'task_type'],
        unique=True,
        postgresql_where=sa.text('is_deleted = false'),
    )


def downgrade() -> None:
    op.drop_index('uix_sku_templates_workspace_task_type', table_name='sku_templates')
    op.drop_index(op.f('ix_sku_templates_workspace_id'), table_name='sku_templates')
    op.drop_index(op.f('ix_sku_templates_created_by_id'), table_name='sku_templates')
    op.drop_table('sku_templates')
