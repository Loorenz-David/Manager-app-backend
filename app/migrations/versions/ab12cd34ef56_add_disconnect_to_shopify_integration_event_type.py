"""add_disconnect_to_shopify_integration_event_type

Revision ID: ab12cd34ef56
Revises: c3f7a9d2e4b1
Create Date: 2026-07-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "ab12cd34ef56"
down_revision: Union[str, None] = "c3f7a9d2e4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE shopify_integration_event_type_enum ADD VALUE IF NOT EXISTS 'disconnect'")


def downgrade() -> None:
    pass