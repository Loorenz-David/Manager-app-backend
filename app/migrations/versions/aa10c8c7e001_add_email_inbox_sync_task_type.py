"""add_email_inbox_sync_task_type

Revision ID: aa10c8c7e001
Revises: 183fb6115bd3, 29c99ef46f70, 38491ecd2b90, 5ad879ec99d9, 869a18698f34, 8cf57fa23110, cf79311a956f
Create Date: 2026-07-04 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "aa10c8c7e001"
down_revision: Union[str, Sequence[str], None] = (
    "183fb6115bd3",
    "29c99ef46f70",
    "38491ecd2b90",
    "5ad879ec99d9",
    "869a18698f34",
    "8cf57fa23110",
    "cf79311a956f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'email_inbox_sync'")


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE from an enum type.
    # Removing 'email_inbox_sync' from task_type_enum is not possible without
    # dropping and recreating the enum and all dependent columns — which is
    # destructive and out of scope for a standard rollback.
    # Acceptance criterion 10 ("all migrations reversible") cannot be fully met
    # for this migration due to this database engine limitation.
    # Safe to leave as no-op: the extra enum value causes no harm in the
    # downgraded schema because the EmailInboxSync task rows will have been
    # removed by the table-drop migrations that run before this one in a
    # full downgrade sequence.
    pass
