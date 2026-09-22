"""Router: /api/v1/location-tracker (Scanner-inbound stock webhooks).

Mounted at the same prefix as the existing `location_tracker.router` (H22 — that
router keeps its own mount and its own `/items/location` route; nothing collides).

Every route goes through `_run_webhook`, which is the one place that records a
delivery: what arrived, and what it decided. The commands themselves stay free of
logging — they are shared by tests and by each other, and the router is the only
layer that sees both the raw body and the final HTTP answer.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.stock_report.process_items_processed import (
    process_items_processed,
)
from beyo_manager.services.commands.stock_report.process_stock_demand_deleted import (
    process_stock_demand_deleted,
)
from beyo_manager.services.commands.stock_report.receive_stock_demand_webhook import (
    receive_stock_demand_webhook,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()

logger = logging.getLogger(__name__)

# A malformed or hostile body must not be able to write an unbounded log line.
_MAX_LOGGED_BODY_CHARS = 4000


def _payload_for_log(raw_body: bytes) -> str | None:
    """The inbound body as text, truncated, or `None` when logging is disabled.

    Never decodes strictly: a body that is not valid UTF-8 is exactly the case
    worth seeing, so it is replaced character by character rather than raised.
    """
    if not settings.stock_webhook_log_payloads:
        return None
    body = raw_body.decode("utf-8", errors="replace")
    if len(body) > _MAX_LOGGED_BODY_CHARS:
        return f"{body[:_MAX_LOGGED_BODY_CHARS]}…[truncated, {len(body)} chars]"
    return body


def _outcome_counts(data: Any) -> dict[str, int] | None:
    """`{"deleted": 2, "not_found": 1}` from a command's `{"results": [...]}`.

    All three commands answer in that shape, one entry per request entry, each
    carrying an `outcome`. Anything else returns `None` rather than guessing.
    """
    if not isinstance(data, dict):
        return None
    results = data.get("results")
    if not isinstance(results, list):
        return None
    counts = Counter(
        str(item.get("outcome")) for item in results if isinstance(item, dict)
    )
    return dict(sorted(counts.items()))


async def _run_webhook(
    webhook: str,
    command: Callable[[ServiceContext], Awaitable[Any]],
    request: Request,
    session: AsyncSession,
):
    """Read the body, run the command, and record both ends of the delivery."""
    raw_body = await request.body()
    started = time.monotonic()

    logger.info(
        "stock webhook received | webhook=%s body_length=%d",
        webhook,
        len(raw_body),
        extra={
            "event_type": "stock_webhook.received",
            "webhook": webhook,
            "path": request.url.path,
            "method": request.method,
            "body_length": len(raw_body),
            # Headers are deliberately never logged: they carry the shared secret
            # the verifier checks.
            "payload": _payload_for_log(raw_body),
        },
    )

    outcome = await run_service(
        command,
        ServiceContext(
            identity={},
            incoming_data={"raw_body": raw_body, "headers": dict(request.headers)},
            session=session,
        ),
    )
    duration_ms = round((time.monotonic() - started) * 1000, 1)

    if not outcome.success:
        error = outcome.error
        logger.warning(
            "stock webhook rejected | webhook=%s status=%s error=%s",
            webhook,
            error.http_status,
            error.message,
            extra={
                "event_type": "stock_webhook.rejected",
                "webhook": webhook,
                "path": request.url.path,
                "status_code": error.http_status,
                "error": f"{type(error).__name__}: {error.message}",
                "duration_ms": duration_ms,
            },
        )
        return build_err(error)

    counts = _outcome_counts(outcome.data)
    logger.info(
        "stock webhook completed | webhook=%s outcomes=%s duration_ms=%s",
        webhook,
        counts,
        duration_ms,
        extra={
            "event_type": "stock_webhook.completed",
            "webhook": webhook,
            "path": request.url.path,
            "status_code": 200,
            "duration_ms": duration_ms,
            "outcomes": counts,
            # The per-entry answers, so a delivery can be reconciled entry by
            # entry against what Scanner sent. Suppressed with the body.
            "results": outcome.data.get("results")
            if settings.stock_webhook_log_payloads and isinstance(outcome.data, dict)
            else None,
        },
    )
    return build_ok(outcome.data)


@router.post("/webhooks/stock-demand")
async def stock_demand_webhook_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    return await _run_webhook(
        "stock-demand", receive_stock_demand_webhook, request, session
    )


@router.post("/webhooks/items-processed")
async def items_processed_webhook_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    return await _run_webhook(
        "items-processed", process_items_processed, request, session
    )


@router.post("/webhooks/stock-demand-deleted")
async def stock_demand_deleted_webhook_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    return await _run_webhook(
        "stock-demand-deleted", process_stock_demand_deleted, request, session
    )
