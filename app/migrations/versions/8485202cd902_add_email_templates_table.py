"""add_email_templates_table

Revision ID: 8485202cd902
Revises: dd861a418d9d
Create Date: 2026-07-04 22:05:12.824058
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '8485202cd902'
down_revision: Union[str, None] = 'dd861a418d9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('email_templates',
    sa.Column('workspace_id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('subject', sa.String(length=512), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('topic', sa.String(length=64), nullable=False),
    sa.Column('template_type', sa.String(length=16), nullable=False),
    sa.Column('created_by_id', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_by_id', sa.String(length=64), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('client_id', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.client_id'], ),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.client_id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.client_id'], ),
    sa.PrimaryKeyConstraint('client_id')
    )
    op.create_index(op.f('ix_email_templates_created_at'), 'email_templates', ['created_at'], unique=False)
    op.create_index(op.f('ix_email_templates_topic'), 'email_templates', ['topic'], unique=False)
    op.create_index(op.f('ix_email_templates_workspace_id'), 'email_templates', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_templates_workspace_id'), table_name='email_templates')
    op.drop_index(op.f('ix_email_templates_topic'), table_name='email_templates')
    op.drop_index(op.f('ix_email_templates_created_at'), table_name='email_templates')
    op.drop_table('email_templates')
