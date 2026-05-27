"""add_favorite_and_list_order_to_upholsteries

Revision ID: 6d7e8f9012ab
Revises: 5c2e7f91ab44
Create Date: 2026-05-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "6d7e8f9012ab"
down_revision: Union[str, None] = "5c2e7f91ab44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "upholsteries",
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("upholsteries", sa.Column("list_order", sa.Integer(), nullable=True))

    op.create_index(
        "uix_upholsteries_workspace_list_order",
        "upholsteries",
        ["workspace_id", "list_order"],
        unique=True,
        postgresql_where=sa.text("list_order IS NOT NULL"),
    )
    op.create_index(
        "ix_upholsteries_workspace_favorite",
        "upholsteries",
        ["workspace_id", "favorite"],
        unique=False,
    )
    op.create_index(
        "ix_upholsteries_workspace_list_order",
        "upholsteries",
        ["workspace_id", "list_order"],
        unique=False,
    )

    op.alter_column("upholsteries", "favorite", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_upholsteries_workspace_list_order", table_name="upholsteries")
    op.drop_index("ix_upholsteries_workspace_favorite", table_name="upholsteries")
    op.drop_index("uix_upholsteries_workspace_list_order", table_name="upholsteries")

    op.drop_column("upholsteries", "list_order")
    op.drop_column("upholsteries", "favorite")
