"""add_upholstery_worker_and_quality_control_to_workspace_role_name_enum

Revision ID: a3b5c7d9e1f2
Revises: 4f2e9a7b6c1d
Create Date: 2026-06-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a3b5c7d9e1f2"
down_revision: Union[str, None] = "4f2e9a7b6c1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE workspace_role_name_enum ADD VALUE 'upholstery_worker'")
    op.execute("ALTER TYPE workspace_role_name_enum ADD VALUE 'quality_control'")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE workspace_roles
        ALTER COLUMN name TYPE VARCHAR(64)
        USING name::text
        """
    )
    op.execute("DROP TYPE workspace_role_name_enum")
    op.execute("CREATE TYPE workspace_role_name_enum AS ENUM ('wood_worker')")
    op.execute(
        """
        ALTER TABLE workspace_roles
        ALTER COLUMN name TYPE workspace_role_name_enum
        USING name::workspace_role_name_enum
        """
    )
