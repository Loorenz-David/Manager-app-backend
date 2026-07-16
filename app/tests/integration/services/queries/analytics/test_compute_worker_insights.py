from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.analytics.compute_worker_insights import compute_worker_insights

TARGET = date(2026, 7, 15)  # a Wednesday


def _ctx(db_session, workspace_id: str) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_mgr", "role_name": "manager", "username": "mgr"},
        incoming_data={},
        query_params={},
        session=db_session,
    )


async def _seed_day(db_session, *, workspace_id, user_id, work_date, working, pause, completed=0):
    db_session.add(
        UserDailyWorkStats(
            workspace_id=workspace_id,
            user_id=user_id,
            user_display_name_snapshot="w",
            work_date=work_date,
            total_working_seconds=working,
            total_pause_seconds=pause,
            total_completed_count=completed,
        )
    )
    await db_session.flush()


@pytest.mark.integration
async def test_compute_worker_insights_fires_from_real_rows(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}", username=f"user_{suffix}",
        email=f"{suffix}@example.com", password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()

    # 4 same-weekday baseline days at focus ratio 0.5, target far higher (~0.95).
    for k in range(1, 5):
        await _seed_day(
            db_session, workspace_id=workspace.client_id, user_id=user.client_id,
            work_date=TARGET - timedelta(days=7 * k), working=1000, pause=1000, completed=3,
        )
    await _seed_day(
        db_session, workspace_id=workspace.client_id, user_id=user.client_id,
        work_date=TARGET, working=1900, pause=100, completed=3,
    )

    result = await compute_worker_insights(_ctx(db_session, workspace.client_id), [user.client_id], TARGET)

    insights = result[user.client_id]
    # deep_focus is intraday-safe, so it fires regardless of whether TARGET is "today".
    assert any(i.code == "deep_focus" and i.polarity == "positive" for i in insights)


@pytest.mark.integration
async def test_compute_worker_insights_empty_without_history(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}", username=f"user_{suffix}",
        email=f"{suffix}@example.com", password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()

    result = await compute_worker_insights(_ctx(db_session, workspace.client_id), [user.client_id], TARGET)
    assert result[user.client_id] == []
