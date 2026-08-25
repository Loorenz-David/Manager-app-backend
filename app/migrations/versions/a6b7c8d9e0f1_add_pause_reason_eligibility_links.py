"""add pause reason eligibility links

Revision ID: a6b7c8d9e0f1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-24 16:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pause_reason_user_links",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("pause_reason_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["pause_reason_id"], ["pause_reasons.client_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "workspace_id",
            "pause_reason_id",
            "user_id",
            name="uq_pause_reason_user_links_target",
        ),
    )
    op.create_index(
        "ix_pause_reason_user_links_workspace_id",
        "pause_reason_user_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_pause_reason_user_links_pause_reason_id",
        "pause_reason_user_links",
        ["pause_reason_id"],
    )
    op.create_index(
        "ix_pause_reason_user_links_user_id",
        "pause_reason_user_links",
        ["user_id"],
    )

    op.create_table(
        "pause_reason_working_section_links",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("pause_reason_id", sa.String(length=64), nullable=False),
        sa.Column("working_section_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["pause_reason_id"], ["pause_reasons.client_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["working_section_id"],
            ["working_sections.client_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "workspace_id",
            "pause_reason_id",
            "working_section_id",
            name="uq_pause_reason_section_links_target",
        ),
    )
    op.create_index(
        "ix_pause_reason_working_section_links_workspace_id",
        "pause_reason_working_section_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_pause_reason_working_section_links_pause_reason_id",
        "pause_reason_working_section_links",
        ["pause_reason_id"],
    )
    op.create_index(
        "ix_pause_reason_working_section_links_working_section_id",
        "pause_reason_working_section_links",
        ["working_section_id"],
    )

    op.execute(
        sa.text(
            """
            UPDATE pause_reasons
            SET slug = 'custom_' || client_id
            WHERE slug IS NULL
            """
        )
    )
    op.alter_column(
        "pause_reasons",
        "slug",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.drop_constraint(
        "uq_pause_reasons_workspace_name",
        "pause_reasons",
        type_="unique",
    )
    op.create_index(
        "uix_pause_reasons_workspace_name_active",
        "pause_reasons",
        ["workspace_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index(
        "uix_pause_reasons_workspace_name_active",
        table_name="pause_reasons",
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_unique_constraint(
        "uq_pause_reasons_workspace_name",
        "pause_reasons",
        ["workspace_id", "name"],
    )
    op.alter_column(
        "pause_reasons",
        "slug",
        existing_type=sa.String(length=64),
        nullable=True,
    )

    op.drop_index(
        "ix_pause_reason_working_section_links_working_section_id",
        table_name="pause_reason_working_section_links",
    )
    op.drop_index(
        "ix_pause_reason_working_section_links_pause_reason_id",
        table_name="pause_reason_working_section_links",
    )
    op.drop_index(
        "ix_pause_reason_working_section_links_workspace_id",
        table_name="pause_reason_working_section_links",
    )
    op.drop_table("pause_reason_working_section_links")

    op.drop_index(
        "ix_pause_reason_user_links_user_id",
        table_name="pause_reason_user_links",
    )
    op.drop_index(
        "ix_pause_reason_user_links_pause_reason_id",
        table_name="pause_reason_user_links",
    )
    op.drop_index(
        "ix_pause_reason_user_links_workspace_id",
        table_name="pause_reason_user_links",
    )
    op.drop_table("pause_reason_user_links")
