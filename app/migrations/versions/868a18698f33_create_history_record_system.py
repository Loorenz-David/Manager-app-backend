"""create_history_record_system

Revision ID: 868a18698f33
Revises: f9de7bfdb842
Create Date: 2026-05-19 07:46:55.470123
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '868a18698f33'
down_revision: Union[str, None] = 'f9de7bfdb842'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_history_record_change_type_enum = postgresql.ENUM(
    "created",
    "updated",
    "deleted",
    name="history_record_change_type_enum",
    create_type=False,
)

_history_record_entity_type_enum = postgresql.ENUM(
    "item",
    "item_upholstery",
    "item_upholstery_requirement",
    "task",
    "case",
    "user",
    name="history_record_entity_type_enum",
    create_type=False,
)


def upgrade() -> None:
    _history_record_change_type_enum.create(op.get_bind(), checkfirst=True)
    _history_record_entity_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "history_records",
        sa.Column("change_type", _history_record_change_type_enum, nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("field_name", sa.String(length=128), nullable=True),
        sa.Column("from_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("to_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.client_id"],
            ondelete="RESTRICT",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(op.f("ix_history_records_change_type"), "history_records", ["change_type"], unique=False)
    op.create_index(op.f("ix_history_records_field_name"), "history_records", ["field_name"], unique=False)
    op.create_index(op.f("ix_history_records_created_at"), "history_records", ["created_at"], unique=False)
    op.create_index(op.f("ix_history_records_created_by_id"), "history_records", ["created_by_id"], unique=False)

    op.create_table(
        "history_record_links",
        sa.Column("history_record_id", sa.String(length=64), nullable=False),
        sa.Column("entity_type", _history_record_entity_type_enum, nullable=False),
        sa.Column("entity_client_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["history_record_id"],
            ["history_records.client_id"],
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(op.f("ix_history_record_links_history_record_id"), "history_record_links", ["history_record_id"], unique=False)
    op.create_index(op.f("ix_history_record_links_entity_type"), "history_record_links", ["entity_type"], unique=False)
    op.create_index(op.f("ix_history_record_links_entity_client_id"), "history_record_links", ["entity_client_id"], unique=False)
    op.create_index(
        "ix_history_record_links_entity_type_client_id",
        "history_record_links",
        ["entity_type", "entity_client_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_history_record_links_entity_type_client_id", table_name="history_record_links")
    op.drop_index(op.f("ix_history_record_links_entity_client_id"), table_name="history_record_links")
    op.drop_index(op.f("ix_history_record_links_entity_type"), table_name="history_record_links")
    op.drop_index(op.f("ix_history_record_links_history_record_id"), table_name="history_record_links")
    op.drop_table("history_record_links")

    op.drop_index(op.f("ix_history_records_created_by_id"), table_name="history_records")
    op.drop_index(op.f("ix_history_records_created_at"), table_name="history_records")
    op.drop_index(op.f("ix_history_records_field_name"), table_name="history_records")
    op.drop_index(op.f("ix_history_records_change_type"), table_name="history_records")
    op.drop_table("history_records")

    _history_record_entity_type_enum.drop(op.get_bind(), checkfirst=True)
    _history_record_change_type_enum.drop(op.get_bind(), checkfirst=True)

