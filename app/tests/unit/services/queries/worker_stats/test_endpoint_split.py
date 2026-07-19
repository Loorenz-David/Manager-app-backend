from types import SimpleNamespace

import pytest

from beyo_manager.services.queries.worker_stats import list_workers_insights as insights_module
from beyo_manager.services.queries.worker_stats import list_workers_last_interacted_step as last_module
from beyo_manager.services.queries.worker_stats import list_workers_totals as totals_module


class _EmptyResult:
    def all(self):
        return []

    def __iter__(self):
        return iter(())


class _EmptySession:
    async def execute(self, _statement):
        return _EmptyResult()


def _ctx():
    return SimpleNamespace(query_params={}, session=_EmptySession(), workspace_id="ws_test")


@pytest.mark.asyncio
async def test_split_services_return_disjoint_worker_shapes(monkeypatch):
    pagination = {"has_more": False, "limit": 50, "offset": 0, "total": 1}
    worker = SimpleNamespace(
        client_id="usr_test",
        username="worker",
        profile_picture=None,
        last_online=None,
    )

    async def empty_page(_ctx):
        return [worker], pagination

    monkeypatch.setattr(last_module, "load_worker_page", empty_page)
    monkeypatch.setattr(totals_module, "load_worker_page", empty_page)
    monkeypatch.setattr(insights_module, "load_worker_page", empty_page)

    last = await last_module.list_workers_last_interacted_step(_ctx())
    totals = await totals_module.list_workers_totals(_ctx())
    insights = await insights_module.list_workers_insights(_ctx())

    assert set(last["workers"][0]) == {"user", "last_interacted_step", "batch"}
    assert set(totals["workers"][0]) == {"user", "daily_stats", "running"}
    assert set(insights["workers"][0]) == {"user", "insights"}
    assert last["workers_pagination"] == totals["workers_pagination"] == insights["workers_pagination"]


def test_worker_stats_router_registers_all_split_routes():
    from beyo_manager.routers.api_v1.worker_stats import router

    paths = {route.path for route in router.routes}
    assert "/last-interacted-steps" in paths
    assert "/totals" in paths
    assert "/insights" in paths
    assert "/{user_id}/daily-steps" in paths
