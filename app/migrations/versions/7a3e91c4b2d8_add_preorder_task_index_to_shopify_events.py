"""add preorder task lookup index to shopify_integration_events

The task flow-records query resolves a task's Shopify events with

    WHERE workspace_id = :ws
      AND event_type = 'preorder'
      AND metadata ->> 'task_id' = :task_id

`shopify_integration_events` grows with every inbound webhook (each delivery writes a
WEBHOOK_RECEIVED and a WEBHOOK_PROCESSED row), so without this index the JSON lookup degrades into
a scan of a table whose size is driven by webhook traffic rather than by pre-order volume.

The index is both **partial** and **functional**:

- partial on `event_type = 'preorder'` — only pre-order events carry a `task_id`, so the index stays
  proportional to pre-orders rather than to the whole table;
- functional on `metadata ->> 'task_id'` — matching the expression the query emits, so the planner
  can use it directly.

Built CONCURRENTLY (following 6787eabf4c32) so adding it does not block writes on a live table.
CONCURRENTLY cannot run inside a transaction, hence the explicit COMMIT first.

Revision ID: 7a3e91c4b2d8
Revises: 2e351577bb18
Create Date: 2026-07-27 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "7a3e91c4b2d8"
down_revision: Union[str, None] = "2e351577bb18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "ix_shopify_integration_events_preorder_task"


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute(
        f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX_NAME} "
        "ON shopify_integration_events (workspace_id, (metadata ->> 'task_id')) "
        "WHERE event_type = 'preorder'"
    )


def downgrade() -> None:
    op.execute("COMMIT")
    op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX_NAME}")
