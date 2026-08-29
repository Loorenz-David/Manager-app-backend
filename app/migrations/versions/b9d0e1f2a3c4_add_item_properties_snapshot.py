"""add item properties snapshot columns and indexes

Revision ID: b9d0e1f2a3c4
Revises: a7b8c9d0e1f2
Create Date: 2026-08-29 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "b9d0e1f2a3c4"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Canonical externally-owned properties snapshot: NULL = no snapshot yet.
    # An empty payload never establishes one, so {} is not persisted here. The
    # signature is derived from the blob at ingestion time and is the narrowing
    # key for the properties complexity tier; the blob itself stays descriptive.
    op.add_column("items", sa.Column("properties", JSONB(), nullable=True))
    op.add_column("items", sa.Column("properties_signature", sa.String(length=64), nullable=True))
    op.add_column("items", sa.Column("properties_snapshot_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_items_workspace_properties_signature",
        "items",
        ["workspace_id", "properties_signature"],
        postgresql_where=sa.text("properties_signature IS NOT NULL AND is_deleted = false"),
    )
    op.create_index(
        "ix_items_properties_gin",
        "items",
        ["properties"],
        postgresql_using="gin",
        postgresql_ops={"properties": "jsonb_path_ops"},
        postgresql_where=sa.text("properties IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_items_properties_gin", table_name="items")
    op.drop_index("ix_items_workspace_properties_signature", table_name="items")
    op.drop_column("items", "properties_snapshot_at")
    op.drop_column("items", "properties_signature")
    op.drop_column("items", "properties")
