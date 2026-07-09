"""add_shopify_product_modification_flag_to_working_sections

Revision ID: d4f8a1b2c3e4
Revises: ab12cd34ef56
Create Date: 2026-07-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a1b2c3e4"
down_revision: Union[str, Sequence[str], None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "working_sections",
        sa.Column(
            "allows_shopify_product_modifications",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("working_sections", "allows_shopify_product_modifications")
