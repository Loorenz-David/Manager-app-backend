"""rename_workspace_role_name_to_specialization

Revision ID: 6f4d2c1b9a7e
Revises: 869a18698f34, 183fb6115bd3, 29c99ef46f70, 5ad879ec99d9, 8cf57fa23110, 38491ecd2b90, cf79311a956f
Create Date: 2026-06-29 15:20:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "6f4d2c1b9a7e"
down_revision: Union[str, Sequence[str], None] = (
    "869a18698f34",
    "183fb6115bd3",
    "29c99ef46f70",
    "5ad879ec99d9",
    "8cf57fa23110",
    "38491ecd2b90",
    "cf79311a956f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE workspace_role_name_enum RENAME TO workspace_role_specialization_enum")
    op.alter_column("workspace_roles", "name", new_column_name="specialization")
    op.drop_constraint("uq_workspace_roles_workspace_name", "workspace_roles", type_="unique")
    op.create_unique_constraint(
        "uq_workspace_roles_workspace_role_specialization",
        "workspace_roles",
        ["workspace_id", "role_id", "specialization"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workspace_roles_workspace_role_specialization",
        "workspace_roles",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_workspace_roles_workspace_name",
        "workspace_roles",
        ["workspace_id", "specialization"],
    )
    op.alter_column("workspace_roles", "specialization", new_column_name="name")
    op.execute("ALTER TYPE workspace_role_specialization_enum RENAME TO workspace_role_name_enum")
