"""cleanup_legacy_history_records

Revision ID: f9de7bfdb842
Revises: 8f2c1d4a7b3e
Create Date: 2026-05-19 07:46:55.312937
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'f9de7bfdb842'
down_revision: Union[str, None] = '8f2c1d4a7b3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_customer_history_change_type_enum = postgresql.ENUM(
    "created",
    "profile_updated",
    "contact_updated",
    "address_updated",
    "status_updated",
    "soft_deleted",
    "restored",
    "merged",
    "redacted",
    "anonymized",
    "correction",
    "retraction",
    name="customer_history_change_type_enum",
    create_type=False,
)


def upgrade() -> None:
    op.drop_constraint("fk_tasks_latest_history_record_id", "tasks", type_="foreignkey")
    op.drop_constraint("fk_customers_latest_history_record_id", "customers", type_="foreignkey")

    op.drop_index(op.f("ix_tasks_latest_history_record_id"), table_name="tasks")
    op.drop_index(op.f("ix_customers_latest_history_record_id"), table_name="customers")

    op.drop_column("tasks", "latest_history_record_id")
    op.drop_column("customers", "latest_history_record_id")

    op.drop_index("ix_task_history_records_workspace_task_occurred", table_name="task_history_records")
    op.drop_index("ix_task_history_records_workspace_task_created", table_name="task_history_records")
    op.drop_index(op.f("ix_task_history_records_workspace_id"), table_name="task_history_records")
    op.drop_index(op.f("ix_task_history_records_task_id"), table_name="task_history_records")
    op.drop_index(op.f("ix_task_history_records_occurred_at"), table_name="task_history_records")
    op.drop_index(op.f("ix_task_history_records_created_by_id"), table_name="task_history_records")
    op.drop_table("task_history_records")

    op.drop_index(op.f("ix_customer_history_records_workspace_id"), table_name="customer_history_records")
    op.drop_index(
        "ix_customer_history_records_workspace_customer_occurred",
        table_name="customer_history_records",
    )
    op.drop_index(
        "ix_customer_history_records_workspace_customer_created",
        table_name="customer_history_records",
    )
    op.drop_index(op.f("ix_customer_history_records_occurred_at"), table_name="customer_history_records")
    op.drop_index(op.f("ix_customer_history_records_customer_id"), table_name="customer_history_records")
    op.drop_index(op.f("ix_customer_history_records_created_by_id"), table_name="customer_history_records")
    op.drop_index(op.f("ix_customer_history_records_change_type"), table_name="customer_history_records")
    op.drop_table("customer_history_records")

    _customer_history_change_type_enum.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    _customer_history_change_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("customers", sa.Column("latest_history_record_id", sa.String(length=64), nullable=True))
    op.add_column("tasks", sa.Column("latest_history_record_id", sa.String(length=64), nullable=True))

    op.create_table(
        "customer_history_records",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=False),
        sa.Column("change_type", _customer_history_change_type_enum, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("change_summary", sa.String(length=512), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(op.f("ix_customer_history_records_change_type"), "customer_history_records", ["change_type"], unique=False)
    op.create_index(op.f("ix_customer_history_records_created_by_id"), "customer_history_records", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_customer_history_records_customer_id"), "customer_history_records", ["customer_id"], unique=False)
    op.create_index(op.f("ix_customer_history_records_occurred_at"), "customer_history_records", ["occurred_at"], unique=False)
    op.create_index(
        "ix_customer_history_records_workspace_customer_created",
        "customer_history_records",
        ["workspace_id", "customer_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_customer_history_records_workspace_customer_occurred",
        "customer_history_records",
        ["workspace_id", "customer_id", "occurred_at"],
        unique=False,
    )
    op.create_index(op.f("ix_customer_history_records_workspace_id"), "customer_history_records", ["workspace_id"], unique=False)

    op.create_table(
        "task_history_records",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("state_from", sa.String(length=64), nullable=True),
        sa.Column("state_to", sa.String(length=64), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column("reason_text", sa.String(length=512), nullable=True),
        sa.Column("snapshot_payload", sa.JSON(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(op.f("ix_task_history_records_created_by_id"), "task_history_records", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_task_history_records_occurred_at"), "task_history_records", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_task_history_records_task_id"), "task_history_records", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_history_records_workspace_id"), "task_history_records", ["workspace_id"], unique=False)
    op.create_index(
        "ix_task_history_records_workspace_task_created",
        "task_history_records",
        ["workspace_id", "task_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_task_history_records_workspace_task_occurred",
        "task_history_records",
        ["workspace_id", "task_id", "occurred_at"],
        unique=False,
    )

    op.create_index(op.f("ix_customers_latest_history_record_id"), "customers", ["latest_history_record_id"], unique=False)
    op.create_index(op.f("ix_tasks_latest_history_record_id"), "tasks", ["latest_history_record_id"], unique=False)

    op.create_foreign_key(
        "fk_customers_latest_history_record_id",
        "customers",
        "customer_history_records",
        ["latest_history_record_id"],
        ["client_id"],
        ondelete="RESTRICT",
        use_alter=True,
    )
    op.create_foreign_key(
        "fk_tasks_latest_history_record_id",
        "tasks",
        "task_history_records",
        ["latest_history_record_id"],
        ["client_id"],
        ondelete="RESTRICT",
        use_alter=True,
    )
