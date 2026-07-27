"""add slide background color

Revision ID: c4e8a1d92f07
Revises: b58cdffb5ccc
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1d92f07"
down_revision: Union[str, None] = "b58cdffb5ccc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_update_presentation_slides",
        sa.Column("background_color", sa.String(length=9), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_update_presentation_slides", "background_color")
