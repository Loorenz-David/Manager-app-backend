"""merge remaining heads after upholstery and role changes

Revision ID: 9a8b7c6d5e4f
Revises: a3b5c7d9e1f2, 3c2d4e5f6a7b
Create Date: 2026-06-29 16:25:00.000000
"""

from typing import Sequence, Union


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = (
    "a3b5c7d9e1f2",
    "3c2d4e5f6a7b",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
