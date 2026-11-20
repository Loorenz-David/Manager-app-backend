"""Inbound API-key check for the pricing app (`GET /api/v1/pricing/item-costs`).

The pricing app deliberately shares the Scanner's inbound key
(`MANAGER_API_KEY_TO_LOCATION_TRACKER_APP`) and workspace
(`LOCATION_TRACKER_WEBHOOK_WORKSPACE_ID`): one secret, two callers, so rotating it
means updating both apps. The check mirrors
`location_tracker/webhook_verifier.py` but logs under its own event type, so a
pricing refusal is never mistaken for a stock-webhook one.
"""

from __future__ import annotations

import hmac
import logging
from collections.abc import Mapping

from beyo_manager.config import settings
from beyo_manager.errors.permissions import PricingApiAuthError

logger = logging.getLogger(__name__)


def refuse_pricing_api_auth(cause: str) -> PricingApiAuthError:
    """One 401 body for every cause. The cause goes to the log only; the key is
    never logged, only whether it matched."""
    logger.warning(
        "pricing api auth refused | cause=%s",
        cause,
        extra={
            "event_type": "pricing_api.auth_refused",
            "cause": cause,
            "status_code": 401,
        },
    )
    return PricingApiAuthError()


def verify_pricing_api_request(headers: Mapping[str, str]) -> str:
    """Return the configured workspace id, or raise the identical 401.

    The caller still has to confirm the workspace row exists
    (`workspace_not_found`), because that needs the session.
    """
    api_key = settings.manager_api_key_to_location_tracker_app
    workspace_id = settings.location_tracker_webhook_workspace_id
    if api_key is None or not api_key.strip():
        raise refuse_pricing_api_auth("server_api_key_not_configured")
    if workspace_id is None or not workspace_id.strip():
        raise refuse_pricing_api_auth("server_workspace_id_not_configured")

    provided = headers.get("x-api-key")
    if provided is None:
        raise refuse_pricing_api_auth("missing_x_api_key_header")

    # Bytes, not str: compare_digest raises TypeError on a non-ASCII str, which
    # would surface as a 500 instead of a 401.
    if not hmac.compare_digest(provided.encode("utf-8"), api_key.encode("utf-8")):
        raise refuse_pricing_api_auth("x_api_key_mismatch")

    return workspace_id
