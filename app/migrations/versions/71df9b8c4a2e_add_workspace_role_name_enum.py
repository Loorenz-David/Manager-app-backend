"""add_workspace_role_name_enum

Revision ID: 71df9b8c4a2e
Revises: 183fb6115bd3
Create Date: 2026-06-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "71df9b8c4a2e"
down_revision: Union[str, None] = "183fb6115bd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE workspace_role_name_enum AS ENUM ('wood_worker')")
    op.execute("ALTER TABLE workspace_roles ALTER COLUMN name DROP NOT NULL")
    op.execute("UPDATE workspace_roles SET name = NULL")
    op.execute(
        """
        ALTER TABLE workspace_roles
        ALTER COLUMN name TYPE workspace_role_name_enum
        USING name::workspace_role_name_enum
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE workspace_roles
        ALTER COLUMN name TYPE VARCHAR(64)
        USING name::text
        """
    )
    op.execute("UPDATE workspace_roles SET name = role.name FROM roles AS role WHERE workspace_roles.role_id = role.client_id")
    op.execute("ALTER TABLE workspace_roles ALTER COLUMN name SET NOT NULL")
    op.execute("DROP TYPE workspace_role_name_enum")
