"""remove sku template scalar padding

Revision ID: 0f86759d0bb5
Revises: 261971b16234
Create Date: 2026-07-23 12:14:54.233837
"""
from typing import Sequence, Union

from alembic import op


revision: str = '0f86759d0bb5'
down_revision: Union[str, None] = '261971b16234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing templates created with the former default (or any explicit
    # padding) are normalized so every configured SKU uses the scalar as-is.
    op.execute("UPDATE sku_templates SET pad_width = 0 WHERE pad_width <> 0")


def downgrade() -> None:
    # The previous per-row pad_width values are not recoverable without a
    # history table. The application default remains no-padding on downgrade.
    pass
