"""Direct unit coverage of `verify_location_tracker_webhook` (master plan §6.5).

The plan 7 criterion table (C1) is discharged through the command
(`test_receive_stock_demand_webhook.py`, per plan 7 task 5: "Integration rows call
the command"). This file is the plan's own file-list entry for the verifier and adds
the one thing the command-level rows do not directly pin: the exact **return value**
on success.
"""

import pytest

from beyo_manager.config import settings
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError
from beyo_manager.services.infra.location_tracker.webhook_verifier import (
    verify_location_tracker_webhook,
)

pytestmark = pytest.mark.unit


def test_returns_the_configured_workspace_id_on_success(monkeypatch):
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", "k")
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", "ws_configured")

    assert verify_location_tracker_webhook({"x-api-key": "k"}) == "ws_configured"


def test_raises_unauthorized_when_key_is_missing_or_wrong(monkeypatch):
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", "k")
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", "ws_configured")

    with pytest.raises(LocationTrackerWebhookAuthError):
        verify_location_tracker_webhook({})
    with pytest.raises(LocationTrackerWebhookAuthError):
        verify_location_tracker_webhook({"x-api-key": "wrong"})
