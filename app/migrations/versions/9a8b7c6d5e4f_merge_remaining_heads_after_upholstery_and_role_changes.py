"""merge remaining heads after upholstery and role changes

Revision ID: 9a8b7c6d5e4f
Revises: 26d4b7f0c3aa, 3c2d4e5f6a7b, 7e1c3b4a9d2f
Create Date: 2026-06-29 16:25:00.000000
"""

from typing import Sequence, Union


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = (
    "26d4b7f0c3aa",
    "3c2d4e5f6a7b",
    "7e1c3b4a9d2f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
