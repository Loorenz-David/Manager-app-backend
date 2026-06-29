"""merge heads after workspace role specialization and case reference

Revision ID: 7e1c3b4a9d2f
Revises: 6f4d2c1b9a7e, d1e2f3a4b5c6
Create Date: 2026-06-29 16:05:00.000000
"""

from typing import Sequence, Union


revision: str = "7e1c3b4a9d2f"
down_revision: Union[str, Sequence[str], None] = ("6f4d2c1b9a7e", "d1e2f3a4b5c6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
