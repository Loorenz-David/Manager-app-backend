"""add completed at to tasks

Revision ID: ce99896e6f49
Revises: b9d0e1f2a3c4
Create Date: 2026-09-09 11:01:04.598698
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'ce99896e6f49'
down_revision: Union[str, None] = 'b9d0e1f2a3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    # RESOLVED: resolve_task stamps the state and closed_at from a single `now`, so closed_at
    # already is the completion timestamp.
    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET completed_at = closed_at
            WHERE state = 'resolved'
              AND closed_at IS NOT NULL
              AND completed_at IS NULL
            """
        )
    )

    # READY had no stored timestamp before this column, so reconstruct it from the work itself:
    # a task flips to READY once its last step reaches a terminal state, and every terminal step
    # transition stamps task_steps.closed_at. Stepless force-ready tasks have no source and stay
    # NULL, which the sort handles with NULLS LAST.
    op.execute(
        sa.text(
            """
            UPDATE tasks AS t
            SET completed_at = s.max_closed_at
            FROM (
                SELECT task_id, MAX(closed_at) AS max_closed_at
                FROM task_steps
                WHERE is_deleted = false
                  AND closed_at IS NOT NULL
                GROUP BY task_id
            ) AS s
            WHERE t.client_id = s.task_id
              AND t.state = 'ready'
              AND t.completed_at IS NULL
            """
        )
    )

    op.create_index(
        "ix_tasks_workspace_state_completed_at",
        "tasks",
        ["workspace_id", "state", "completed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_workspace_state_completed_at", table_name="tasks")
    op.drop_column("tasks", "completed_at")
