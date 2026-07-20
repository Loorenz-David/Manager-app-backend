"""add_connecteam_user_id_to_work_profiles

Revision ID: d0f2a3b4c5d6
Revises: c9e1f2a3b4c5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0f2a3b4c5d6"
down_revision: Union[str, None] = "c9e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_work_profiles", sa.Column("connecteam_user_id", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_user_work_profiles_connecteam_user_id",
        "user_work_profiles",
        ["connecteam_user_id"],
    )
    op.create_unique_constraint(
        "uq_user_work_profiles_workspace_connecteam_user",
        "user_work_profiles",
        ["workspace_id", "connecteam_user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_user_work_profiles_workspace_connecteam_user",
        "user_work_profiles",
        type_="unique",
    )
    op.drop_index("ix_user_work_profiles_connecteam_user_id", table_name="user_work_profiles")
    op.drop_column("user_work_profiles", "connecteam_user_id")

