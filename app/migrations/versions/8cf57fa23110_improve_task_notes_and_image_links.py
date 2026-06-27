"""improve_task_notes_and_image_links

Revision ID: 8cf57fa23110
Revises: a3b5c7d9e1f2
Create Date: 2026-06-26 12:53:34.374140
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '8cf57fa23110'
down_revision: Union[str, None] = 'a3b5c7d9e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE image_link_entity_type_enum ADD VALUE IF NOT EXISTS 'note'")
    op.execute("ALTER TYPE image_events_type_enum ADD VALUE IF NOT EXISTS 'upload_note_image'")
    op.add_column('image_links', sa.Column('major_entity_type', sa.String(length=64), nullable=True))
    op.add_column('image_links', sa.Column('major_entity_client_id', sa.String(length=128), nullable=True))
    op.add_column('task_notes', sa.Column('plain_text', sa.Text(), nullable=True))
    op.add_column(
        'task_notes',
        sa.Column(
            'users_read_list',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('task_notes', 'users_read_list')
    op.drop_column('task_notes', 'plain_text')
    op.drop_column('image_links', 'major_entity_client_id')
    op.drop_column('image_links', 'major_entity_type')
    # PostgreSQL enum values cannot be removed in place.
