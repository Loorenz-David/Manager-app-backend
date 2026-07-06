"""merge_email_head_with_task_post_handling

Revision ID: aa10c8c7e008
Revises: 3c4d5e6f7a8b, aa10c8c7e007
Create Date: 2026-07-04 13:40:00.000000
"""

from typing import Sequence, Union


revision: str = "aa10c8c7e008"
down_revision: Union[str, Sequence[str], None] = ("3c4d5e6f7a8b", "aa10c8c7e007")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
