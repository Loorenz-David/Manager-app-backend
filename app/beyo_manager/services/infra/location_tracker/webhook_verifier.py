"""Scanner stock webhook auth — MC-8 steps 2-3 (intention §8B; master plan §6.5).

Shared by all three Scanner "stock message" webhooks (demand — phase 7; items
processed — phase 9; demand-deleted — phase 13A). `bm/services/infra/location_tracker/`
already exists for the (unrelated) outbound `LocationTrackerClient`; this module is
the new inbound half.
"""

from __future__ import annotations

import hmac
import logging
from collections.abc import Mapping

from beyo_manager.config import settings
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError

logger = logging.getLogger(__name__)


def refuse_webhook_auth(cause: str) -> LocationTrackerWebhookAuthError:
    """One 401 body, five causes. The cause is written to the log and never to
    the response, so telling the failures apart while testing does not tell a
    caller which of them it hit. The key itself is never logged, only whether it
    matched.

    Shared with MC-8 step 4 (`workspace_not_found`), which the three commands
    check for themselves after this verifier has returned.
    """
    logger.warning(
        "location_tracker webhook auth refused | cause=%s",
        cause,
        extra={
            "event_type": "stock_webhook.auth_refused",
            "cause": cause,
            "status_code": 401,
        },
    )
    return LocationTrackerWebhookAuthError("Unauthorized.")


def verify_location_tracker_webhook(headers: Mapping[str, str]) -> str:
    """MC-8 steps 2-3. Returns the configured workspace id on success.

    Every failure raises the identical `LocationTrackerWebhookAuthError("Unauthorized.")`
    — the cause is never returned, only logged (`refuse_webhook_auth`).
    """
    api_key = settings.manager_api_key_to_location_tracker_app
    workspace_id = settings.location_tracker_webhook_workspace_id
    if api_key is None or not api_key.strip():
        raise refuse_webhook_auth("server_api_key_not_configured")
    if workspace_id is None or not workspace_id.strip():
        raise refuse_webhook_auth("server_workspace_id_not_configured")

    provided = headers.get("x-api-key")
    if provided is None:
        raise refuse_webhook_auth("missing_x_api_key_header")

    # Bytes, not str, in compare_digest (MC-8; C24): the str form raises TypeError on
    # a non-ASCII header, surfacing as a 500 instead of a 401 (the connecteam
    # precedent's defect, not copied). `str.encode("utf-8")` never raises for any
    # Python str, so a non-ASCII header simply fails to match here — 401, not 500.
    if not hmac.compare_digest(provided.encode("utf-8"), api_key.encode("utf-8")):
        raise refuse_webhook_auth("x_api_key_mismatch")

    return workspace_id
