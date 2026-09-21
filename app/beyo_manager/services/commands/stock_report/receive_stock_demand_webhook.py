"""`receive_stock_demand_webhook` — the demand webhook's owning command (phase 7;
master plan §6.5; intention §8B).

deadline -> verify -> parse -> apply_stock_demand -> dispatch -> response, in that
order. Never reads `ctx.workspace_id` (it is `""` on a webhook path, §2.5) — the
workspace comes from the verifier's return value.
"""

from __future__ import annotations

import time

from beyo_manager.config import settings
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.stock_demand_request import (
    parse_stock_demand_body,
)
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.location_tracker.webhook_verifier import (
    verify_location_tracker_webhook,
)


async def receive_stock_demand_webhook(ctx) -> dict:
    timeout_ms = settings.stock_demand_webhook_timeout_ms
    deadline = time.monotonic() + timeout_ms / 1000  # first line — MC-9 part 1

    workspace_id = verify_location_tracker_webhook(ctx.incoming_data["headers"])
    entries = parse_stock_demand_body(ctx.incoming_data["raw_body"])

    result = await apply_stock_demand(
        ctx.session,
        workspace_id=workspace_id,
        entries=entries,
        now=ctx.now,
        deadline=deadline,
        timeout_ms=timeout_ms,
    )
    await dispatch(result.events)

    outcome_by_index = {outcome.index: outcome for outcome in result.outcomes}
    results = [
        {
            "itemCategory": outcome_by_index[index].item_category_raw,
            "properties": outcome_by_index[index].properties_raw,
            "outcome": outcome_by_index[index].outcome.value,
        }
        for index in sorted(outcome_by_index)
    ]
    return {"results": results}
