from __future__ import annotations

from dataclasses import replace

import pytest

from beyo_manager.domain.connecteam.time_activity_event import ConnecteamTimeActivityEvent
from beyo_manager.services.queries.users.resolve_connecteam_worker import ResolvedConnecteamWorker


@pytest.fixture
def connecteam_worker() -> ResolvedConnecteamWorker:
    return ResolvedConnecteamWorker(
        work_profile_id="uwp_test",
        user_id="usr_worker",
        workspace_id="ws_test",
    )


@pytest.fixture
def connecteam_event() -> ConnecteamTimeActivityEvent:
    return ConnecteamTimeActivityEvent(
        event_key="connecteam:req-test",
        provider="connecteam",
        event_type="clock_in",
        activity_type="shift",
        request_id="req-test",
        company_id="company-test",
        connecteam_user_id="connecteam-worker",
        time_clock_id="clock-test",
        time_activity_id="activity-test",
        occurred_at="2026-07-20T08:00:00Z",
        received_at="2026-07-20T08:00:02+00:00",
        payload={},
    )


@pytest.fixture
def event_for(connecteam_event):
    missing = object()

    def _event(event_type: str, *, occurred_at: str | None | object = missing):
        return replace(
            connecteam_event,
            event_type=event_type,
            occurred_at=(
                connecteam_event.occurred_at if occurred_at is missing else occurred_at
            ),
        )

    return _event
