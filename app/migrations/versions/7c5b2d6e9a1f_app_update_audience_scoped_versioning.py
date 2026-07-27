"""app_update audience-scoped versioning + category

Adds the presentation `category` column, drops the "one live published version
per logical announcement" partial-unique index (replaced by newest-version-wins
resolution at query time), and adds a supporting (logical_client_id, version)
index.

Revision ID: 7c5b2d6e9a1f
Revises: 6b4a1295bb07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c5b2d6e9a1f"
down_revision: Union[str, None] = "6b4a1295bb07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CATEGORY_ENUM = sa.Enum(
    "improvement",
    "workflow",
    "news",
    "alert",
    name="app_update_presentation_category_enum",
)


def upgrade() -> None:
    _CATEGORY_ENUM.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "app_update_presentations",
        sa.Column("category", _CATEGORY_ENUM, nullable=True),
    )
    # Newest-version-wins replaces the single-live-version constraint.
    op.drop_index(
        "uix_app_update_presentations_one_published",
        table_name="app_update_presentations",
    )
    op.create_index(
        "ix_app_update_presentations_logical_version",
        "app_update_presentations",
        ["logical_client_id", "version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_app_update_presentations_logical_version",
        table_name="app_update_presentations",
    )
    op.create_index(
        "uix_app_update_presentations_one_published",
        "app_update_presentations",
        ["logical_client_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published' AND is_deleted = false"),
    )
    op.drop_column("app_update_presentations", "category")
    op.execute("DROP TYPE IF EXISTS app_update_presentation_category_enum")
