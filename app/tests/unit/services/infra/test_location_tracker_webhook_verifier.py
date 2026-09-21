"""Direct unit coverage of `verify_location_tracker_webhook` (master plan §6.5).

The plan 7 criterion table (C1) is discharged through the command
(`test_receive_stock_demand_webhook.py`, per plan 7 task 5: "Integration rows call
the command"). This file is the plan's own file-list entry for the verifier and adds
the one thing the command-level rows do not directly pin: the exact **return value**
on success.

**Fix round 1 (batch B2, 2026-09-21) — S2.** This file used to carry a second test,
`test_raises_unauthorized_when_key_is_missing_or_wrong`, that traced to no criterion
row and duplicated plan 7 C1(d)/C1(e) at a narrower scope (review 1 finding S2:
charter rule 16). Deleted rather than declared: it added no coverage the command-level
C1(d)/C1(e) rows do not already provide, and this file's own stated purpose above is
"the one thing the command-level rows do not directly pin" — a purpose the deleted
test never served. `test_returns_the_configured_workspace_id_on_success` below is its
surviving sibling and *is* declared, per S2, as a candidate criterion: it is the only
test that pins the verifier's return value, which plan 7 C6(a) otherwise proves only
indirectly (through the row and dispatched event carrying the right workspace, not
through the verifier's own output). Routed as carry-forward CF-4 in plan 7's Review
log for the coordinator to fold into a criterion row or refuse with a recorded reason.
"""

import pytest

from beyo_manager.config import settings
from beyo_manager.services.infra.location_tracker.webhook_verifier import (
    verify_location_tracker_webhook,
)

pytestmark = pytest.mark.unit


def test_returns_the_configured_workspace_id_on_success(monkeypatch):
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", "k")
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", "ws_configured")

    assert verify_location_tracker_webhook({"x-api-key": "k"}) == "ws_configured"
