"""Scanner stock webhook auth — MC-8 steps 2-3 (intention §8B; master plan §6.5).

Shared by all three Scanner "stock message" webhooks (demand — phase 7; items
processed — phase 9; demand-deleted — phase 13A). `bm/services/infra/location_tracker/`
already exists for the (unrelated) outbound `LocationTrackerClient`; this module is
the new inbound half.
"""

from __future__ import annotations

import hmac
from collections.abc import Mapping

from beyo_manager.config import settings
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError


def verify_location_tracker_webhook(headers: Mapping[str, str]) -> str:
    """MC-8 steps 2-3. Returns the configured workspace id on success.

    Every failure raises the identical `LocationTrackerWebhookAuthError("Unauthorized.")`
    — the cause is never returned, only logged by the caller if it chooses to.
    """
    api_key = settings.manager_api_key_to_location_tracker_app
    workspace_id = settings.location_tracker_webhook_workspace_id
    if api_key is None or not api_key.strip():
        raise LocationTrackerWebhookAuthError("Unauthorized.")
    if workspace_id is None or not workspace_id.strip():
        raise LocationTrackerWebhookAuthError("Unauthorized.")

    provided = headers.get("x-api-key")
    if provided is None:
        raise LocationTrackerWebhookAuthError("Unauthorized.")

    # Bytes, not str, in compare_digest (MC-8; C24): the str form raises TypeError on
    # a non-ASCII header, surfacing as a 500 instead of a 401 (the connecteam
    # precedent's defect, not copied). `str.encode("utf-8")` never raises for any
    # Python str, so a non-ASCII header simply fails to match here — 401, not 500.
    if not hmac.compare_digest(provided.encode("utf-8"), api_key.encode("utf-8")):
        raise LocationTrackerWebhookAuthError("Unauthorized.")

    return workspace_id
