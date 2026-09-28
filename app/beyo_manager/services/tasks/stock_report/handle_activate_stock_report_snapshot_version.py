"""Worker handler for a scheduled draft activation (stock-report draft versions,
plan §5.1). Fed by the delayed scheduler: `delayed-scheduler` fires the row,
`task-router` routes the task to `queue:tasks`, `tasks-worker` runs this.

It calls `activate_stock_report_snapshot_version` **directly, not through
`run_service`**, as the scheduling user, with `expected_scheduled_activation_at` in
the body — the one thing that makes an activation "scheduled" (R-6). The outcomes:

- activated — logged;
- `{"skipped": reason}` — superseded (moved, hand-published, later plan due); the
  command has already committed whatever the skip writes. Logged at info under the
  `STOCK_REPORT_SCHEDULE_SUPERSEDED` token (a log identity, never an HTTP response);
- a `DomainError` — the draft was deleted (404) or is no longer a draft (activated
  by hand first): logged at info and completed, **no retry** (P-6);
- anything else propagates, so the worker's normal retry applies.
"""

from __future__ import annotations

import logging

from beyo_manager.domain.execution.payloads.stock_report_version_activation import (
    StockReportVersionActivationPayload,
)
from beyo_manager.errors.base import DomainError
from beyo_manager.models.database import get_db_session
from beyo_manager.services.commands.stock_report.activate_stock_report_snapshot_version import (
    activate_stock_report_snapshot_version,
)
from beyo_manager.services.context import ServiceContext

logger = logging.getLogger(__name__)


async def handle_activate_stock_report_snapshot_version(
    payload: dict, task_client_id: str
) -> None:
    data = StockReportVersionActivationPayload(**payload)
    async for session in get_db_session():
        ctx = ServiceContext(
            identity={
                "workspace_id": data.workspace_id,
                "user_id": data.scheduled_by_user_id or "",
            },
            incoming_data={
                "client_id": data.version_id,
                "expected_scheduled_activation_at": data.scheduled_for,
            },
            session=session,
        )
        try:
            result = await activate_stock_report_snapshot_version(ctx)
        except DomainError as exc:
            logger.info(
                "stock_report_scheduled_activation | not_activated | version_id=%s "
                "task_id=%s reason=%s",
                data.version_id,
                task_client_id,
                exc,
            )
            return
        if "skipped" in result:
            logger.info(
                "STOCK_REPORT_SCHEDULE_SUPERSEDED: scheduled activation skipped | "
                "reason=%s version_id=%s scheduled_for=%s task_id=%s",
                result["skipped"],
                data.version_id,
                data.scheduled_for,
                task_client_id,
            )
            return
        logger.info(
            "stock_report_scheduled_activation | activated | version_id=%s "
            "scheduled_for=%s task_id=%s",
            data.version_id,
            data.scheduled_for,
            task_client_id,
        )
        return
