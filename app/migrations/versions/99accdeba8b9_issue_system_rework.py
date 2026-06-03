"""issue_system_rework

Revision ID: 99accdeba8b9
Revises: b7c4e1d2a9f0
Create Date: 2026-06-03 10:25:35.011536
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "99accdeba8b9"
down_revision: Union[str, None] = "b7c4e1d2a9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_item_issue_state_enum = postgresql.ENUM(
    "pending",
    "fixing",
    "blocked",
    "deferred",
    "skipped",
    "resolved",
    name="item_issue_state_enum",
    create_type=False,
)

_issue_source_enum_without_manual = postgresql.ENUM(
    "internal_inspection",
    "customer",
    "supplier",
    "imported",
    name="issue_source_enum",
    create_type=False,
)


def upgrade() -> None:
    op.execute("ALTER TYPE issue_source_enum ADD VALUE IF NOT EXISTS 'manual'")

    op.create_table(
        "item_category_issue_types",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("item_category_id", sa.String(length=64), nullable=False),
        sa.Column("issue_type_id", sa.String(length=64), nullable=False),
        sa.Column("placement_of_issue", sa.String(length=255), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["issue_type_id"], ["issue_types.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_category_id"], ["item_categories.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "workspace_id",
            "item_category_id",
            "issue_type_id",
            name="uq_item_category_issue_types_unique",
        ),
    )
    op.create_index(
        op.f("ix_item_category_issue_types_issue_type_id"),
        "item_category_issue_types",
        ["issue_type_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_item_category_issue_types_item_category_id"),
        "item_category_issue_types",
        ["item_category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_item_category_issue_types_workspace_id"),
        "item_category_issue_types",
        ["workspace_id"],
        unique=False,
    )

    op.drop_index("ix_issue_category_configs_created_by_id", table_name="issue_category_configs")
    op.drop_index("ix_issue_category_configs_issue_type_id", table_name="issue_category_configs")
    op.drop_index("ix_issue_category_configs_item_category_id", table_name="issue_category_configs")
    op.drop_index("ix_issue_category_configs_workspace_id", table_name="issue_category_configs")
    op.drop_table("issue_category_configs")

    op.add_column("item_issues", sa.Column("step_id", sa.String(length=64), nullable=True))
    op.add_column("item_issues", sa.Column("worker_id", sa.String(length=64), nullable=True))
    op.add_column("item_issues", sa.Column("working_section_id", sa.String(length=64), nullable=True))
    op.add_column("item_issues", sa.Column("item_category_id", sa.String(length=64), nullable=True))
    op.add_column("item_issues", sa.Column("issue_type_snapshot", sa.String(length=255), nullable=True))
    op.add_column("item_issues", sa.Column("placement_of_issue_snapshot", sa.String(length=255), nullable=True))
    op.add_column("item_issues", sa.Column("intensity", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_item_issues_intensity_positive",
        "item_issues",
        "intensity >= 1",
    )

    op.drop_index("ix_item_issues_created_by_id", table_name="item_issues")
    op.drop_index("ix_item_issues_issue_severity_id", table_name="item_issues")
    op.drop_index("ix_item_issues_state", table_name="item_issues")
    op.drop_index("ix_item_issues_workspace_item_state", table_name="item_issues")
    op.drop_index("ix_item_issues_workspace_state", table_name="item_issues")

    op.create_index(op.f("ix_item_issues_item_category_id"), "item_issues", ["item_category_id"], unique=False)
    op.create_index(op.f("ix_item_issues_step_id"), "item_issues", ["step_id"], unique=False)
    op.create_index(op.f("ix_item_issues_worker_id"), "item_issues", ["worker_id"], unique=False)
    op.create_index(
        op.f("ix_item_issues_working_section_id"),
        "item_issues",
        ["working_section_id"],
        unique=False,
    )
    op.create_index("ix_item_issues_workspace_item", "item_issues", ["workspace_id", "item_id"], unique=False)
    op.create_index("ix_item_issues_workspace_step", "item_issues", ["workspace_id", "step_id"], unique=False)

    op.drop_constraint("item_issues_created_by_id_fkey", "item_issues", type_="foreignkey")
    op.drop_constraint("item_issues_updated_by_id_fkey", "item_issues", type_="foreignkey")
    op.drop_constraint("item_issues_issue_severity_id_fkey", "item_issues", type_="foreignkey")
    op.drop_constraint("ck_item_issues_base_time_positive", "item_issues", type_="check")
    op.drop_constraint("ck_item_issues_time_multiplier_positive", "item_issues", type_="check")
    op.create_foreign_key(
        "item_issues_step_id_fkey",
        "item_issues",
        "task_steps",
        ["step_id"],
        ["client_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "item_issues_worker_id_fkey",
        "item_issues",
        "users",
        ["worker_id"],
        ["client_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "item_issues_working_section_id_fkey",
        "item_issues",
        "working_sections",
        ["working_section_id"],
        ["client_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "item_issues_item_category_id_fkey",
        "item_issues",
        "item_categories",
        ["item_category_id"],
        ["client_id"],
        ondelete="RESTRICT",
    )

    op.drop_column("item_issues", "severity_name_snapshot")
    op.drop_column("item_issues", "base_time_seconds")
    op.drop_column("item_issues", "resolved_at")
    op.drop_column("item_issues", "started_at")
    op.drop_column("item_issues", "state")
    op.drop_column("item_issues", "issue_severity_id")
    op.drop_column("item_issues", "updated_by_id")
    op.drop_column("item_issues", "issue_name_snapshot")
    op.drop_column("item_issues", "created_by_id")
    op.drop_column("item_issues", "time_multiplier")

    op.drop_index("ix_issue_severities_created_by_id", table_name="issue_severities")
    op.drop_index("ix_issue_severities_workspace_id", table_name="issue_severities")
    op.drop_table("issue_severities")

    _item_issue_state_enum.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    _item_issue_state_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("item_issues", sa.Column("time_multiplier", sa.Numeric(precision=8, scale=4), nullable=True))
    op.add_column("item_issues", sa.Column("created_by_id", sa.String(length=64), nullable=True))
    op.add_column("item_issues", sa.Column("issue_name_snapshot", sa.String(length=255), nullable=True))
    op.add_column("item_issues", sa.Column("updated_by_id", sa.String(length=64), nullable=True))
    op.add_column("item_issues", sa.Column("issue_severity_id", sa.String(length=64), nullable=True))
    op.add_column("item_issues", sa.Column("state", _item_issue_state_enum, nullable=True))
    op.add_column("item_issues", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("item_issues", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("item_issues", sa.Column("base_time_seconds", sa.Integer(), nullable=True))
    op.add_column("item_issues", sa.Column("severity_name_snapshot", sa.String(length=255), nullable=True))

    op.drop_constraint("item_issues_step_id_fkey", "item_issues", type_="foreignkey")
    op.drop_constraint("item_issues_worker_id_fkey", "item_issues", type_="foreignkey")
    op.drop_constraint("item_issues_working_section_id_fkey", "item_issues", type_="foreignkey")
    op.drop_constraint("item_issues_item_category_id_fkey", "item_issues", type_="foreignkey")

    op.drop_index("ix_item_issues_workspace_step", table_name="item_issues")
    op.drop_index("ix_item_issues_workspace_item", table_name="item_issues")
    op.drop_index(op.f("ix_item_issues_working_section_id"), table_name="item_issues")
    op.drop_index(op.f("ix_item_issues_worker_id"), table_name="item_issues")
    op.drop_index(op.f("ix_item_issues_step_id"), table_name="item_issues")
    op.drop_index(op.f("ix_item_issues_item_category_id"), table_name="item_issues")
    op.drop_constraint("ck_item_issues_intensity_positive", "item_issues", type_="check")

    op.drop_column("item_issues", "intensity")
    op.drop_column("item_issues", "placement_of_issue_snapshot")
    op.drop_column("item_issues", "issue_type_snapshot")
    op.drop_column("item_issues", "item_category_id")
    op.drop_column("item_issues", "working_section_id")
    op.drop_column("item_issues", "worker_id")
    op.drop_column("item_issues", "step_id")

    op.create_table(
        "issue_severities",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("time_multiplier", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_id", sa.String(length=64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.CheckConstraint("time_multiplier >= 0::numeric", name="ck_issue_severities_time_multiplier_positive"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_issue_severities_workspace_name"),
    )
    op.create_index("ix_issue_severities_workspace_id", "issue_severities", ["workspace_id"], unique=False)
    op.create_index("ix_issue_severities_created_by_id", "issue_severities", ["created_by_id"], unique=False)

    op.create_table(
        "issue_category_configs",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("issue_type_id", sa.String(length=64), nullable=False),
        sa.Column("item_category_id", sa.String(length=64), nullable=False),
        sa.Column("base_time_seconds", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_id", sa.String(length=64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.CheckConstraint("base_time_seconds >= 0", name="ck_issue_category_configs_base_time_positive"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_issue_category_configs_effective_window",
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["issue_type_id"], ["issue_types.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_category_id"], ["item_categories.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "workspace_id",
            "issue_type_id",
            "item_category_id",
            "effective_from",
            name="uq_issue_category_configs_unique",
        ),
    )
    op.create_index("ix_issue_category_configs_workspace_id", "issue_category_configs", ["workspace_id"], unique=False)
    op.create_index(
        "ix_issue_category_configs_item_category_id",
        "issue_category_configs",
        ["item_category_id"],
        unique=False,
    )
    op.create_index(
        "ix_issue_category_configs_issue_type_id",
        "issue_category_configs",
        ["issue_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_issue_category_configs_created_by_id",
        "issue_category_configs",
        ["created_by_id"],
        unique=False,
    )

    op.create_foreign_key(
        "item_issues_issue_severity_id_fkey",
        "item_issues",
        "issue_severities",
        ["issue_severity_id"],
        ["client_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "item_issues_updated_by_id_fkey",
        "item_issues",
        "users",
        ["updated_by_id"],
        ["client_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "item_issues_created_by_id_fkey",
        "item_issues",
        "users",
        ["created_by_id"],
        ["client_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_item_issues_workspace_state", "item_issues", ["workspace_id", "state"], unique=False)
    op.create_index(
        "ix_item_issues_workspace_item_state",
        "item_issues",
        ["workspace_id", "item_id", "state"],
        unique=False,
    )
    op.create_index("ix_item_issues_state", "item_issues", ["state"], unique=False)
    op.create_index("ix_item_issues_issue_severity_id", "item_issues", ["issue_severity_id"], unique=False)
    op.create_index("ix_item_issues_created_by_id", "item_issues", ["created_by_id"], unique=False)
    op.create_check_constraint(
        "ck_item_issues_base_time_positive",
        "item_issues",
        "base_time_seconds IS NULL OR base_time_seconds >= 0",
    )
    op.create_check_constraint(
        "ck_item_issues_time_multiplier_positive",
        "item_issues",
        "time_multiplier IS NULL OR time_multiplier >= 0",
    )

    op.drop_index(op.f("ix_item_category_issue_types_workspace_id"), table_name="item_category_issue_types")
    op.drop_index(op.f("ix_item_category_issue_types_item_category_id"), table_name="item_category_issue_types")
    op.drop_index(op.f("ix_item_category_issue_types_issue_type_id"), table_name="item_category_issue_types")
    op.drop_table("item_category_issue_types")

    op.execute("UPDATE issue_types SET source = 'internal_inspection' WHERE source = 'manual'")
    op.execute("ALTER TYPE issue_source_enum RENAME TO issue_source_enum_old")
    _issue_source_enum_without_manual.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE issue_types ALTER COLUMN source TYPE issue_source_enum "
        "USING source::text::issue_source_enum"
    )
    op.execute("DROP TYPE issue_source_enum_old")
