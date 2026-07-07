"""rename_customer_type_person_to_private

Revision ID: 6b4c2d1e9f7a
Revises: 03cfb5308256
Create Date: 2026-07-07 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "6b4c2d1e9f7a"
down_revision: Union[str, None] = "03cfb5308256"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE customer_type_enum RENAME VALUE 'person' TO 'private'")


def downgrade() -> None:
    op.execute("ALTER TYPE customer_type_enum RENAME VALUE 'private' TO 'person'")
