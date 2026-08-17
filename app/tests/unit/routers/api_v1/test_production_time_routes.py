import pytest

from tests.unit.routers.api_v1.test_item_economics_router import _client
from beyo_manager.routers.api_v1 import item_economics


@pytest.mark.unit
@pytest.mark.parametrize("role_name", ["admin", "manager", "worker", "seller"])
def test_production_time_route_is_available_to_all_roles(role_name, monkeypatch):
    client, calls = _client(monkeypatch, role_name)
    response = client.get("/api/v1/item-economics/tasks/tsk_1/production-time")
    assert response.status_code == 200
    assert calls[0][0] is item_economics.get_task_production_time
    assert calls[0][1].incoming_data == {"task_client_id": "tsk_1"}


@pytest.mark.unit
def test_production_time_route_is_time_only_and_has_no_response_model():
    route = next(route for route in item_economics.router.routes if route.path.endswith("/production-time"))
    assert route.response_model is None
    assert route.endpoint.__annotations__.get("return") is None
