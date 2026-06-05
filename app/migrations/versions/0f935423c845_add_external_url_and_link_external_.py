"""add_external_url_and_link_external_image_to_image_enums

Revision ID: 0f935423c845
Revises: 0f7d4c2b1e9a
Create Date: 2026-06-04 15:05:04.020292
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0f935423c845"
down_revision: Union[str, None] = "0f7d4c2b1e9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE image_source_type_enum ADD VALUE IF NOT EXISTS 'external_url'")
    op.execute("ALTER TYPE image_events_type_enum ADD VALUE IF NOT EXISTS 'link_external_image'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass
