"""update_role_name_enum_worker_manager_seller

Revision ID: ec9017a0245c
Revises: 243e62bcd858
Create Date: 2026-05-15 14:31:23.549894
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'ec9017a0245c'
down_revision: Union[str, None] = '243e62bcd858'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Cascade-clean rows that reference the removed enum values.
    # Order: memberships -> workspace_roles -> roles (child -> parent).
    op.execute(
        """
        DELETE FROM workspace_memberships
        WHERE workspace_role_id IN (
            SELECT client_id
            FROM workspace_roles
            WHERE role_id IN (
                SELECT client_id
                FROM roles
                WHERE name IN ('member', 'field')
            )
        )
        """
    )
    op.execute(
        """
        DELETE FROM workspace_roles
        WHERE role_id IN (
            SELECT client_id
            FROM roles
            WHERE name IN ('member', 'field')
        )
        """
    )
    op.execute("DELETE FROM roles WHERE name IN ('member', 'field')")

    # Step 2: Recreate the enum type with the new value set.
    op.execute("CREATE TYPE role_name_enum_new AS ENUM ('admin', 'worker', 'manager', 'seller')")
    op.execute(
        """
        ALTER TABLE roles
        ALTER COLUMN name TYPE role_name_enum_new
        USING name::text::role_name_enum_new
        """
    )
    op.execute("DROP TYPE role_name_enum")
    op.execute("ALTER TYPE role_name_enum_new RENAME TO role_name_enum")


def downgrade() -> None:
    # Step 1: Cascade-clean rows that reference the new enum values before reverting.
    # Order remains child -> parent.
    op.execute(
        """
        DELETE FROM workspace_memberships
        WHERE workspace_role_id IN (
            SELECT client_id
            FROM workspace_roles
            WHERE role_id IN (
                SELECT client_id
                FROM roles
                WHERE name IN ('worker', 'manager', 'seller')
            )
        )
        """
    )
    op.execute(
        """
        DELETE FROM workspace_roles
        WHERE role_id IN (
            SELECT client_id
            FROM roles
            WHERE name IN ('worker', 'manager', 'seller')
        )
        """
    )
    op.execute("DELETE FROM roles WHERE name IN ('worker', 'manager', 'seller')")

    # Step 2: Recreate the original enum type.
    # Note: admin rows survive; member/field rows are not restored.
    op.execute("CREATE TYPE role_name_enum_old AS ENUM ('admin', 'member', 'field')")
    op.execute(
        """
        ALTER TABLE roles
        ALTER COLUMN name TYPE role_name_enum_old
        USING name::text::role_name_enum_old
        """
    )
    op.execute("DROP TYPE role_name_enum")
    op.execute("ALTER TYPE role_name_enum_old RENAME TO role_name_enum")
