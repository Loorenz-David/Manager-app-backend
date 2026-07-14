from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import shopify as shopify_router
from tests.unit.test_shopify_router import _build_test_client


@pytest.mark.unit
def test_batch_metafield_preference_create_route_forwards_body_and_returns_list(monkeypatch) -> None:
    result = {
        "client_id": "shpmfp_1",
        "item_category_id": "icat_1",
        "shop_integration_id": "shpint_1",
        "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/1",
        "name": "Seat height",
        "namespace": "custom",
        "key": "seat_height",
        "description": None,
        "type": "dimension",
        "validations": [],
        "sequence_order": 0,
        "is_enabled": True,
        "created_at": "2026-07-13T00:00:00+00:00",
        "updated_at": None,
        "created_by": None,
    }
    client, captured = _build_test_client(
        claims={"role_name": "seller", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data=[result], error=None),
    )
    payload = {
        "item_category_id": "icat_1",
        "preferences": [
            {
                "client_id": "shpmfp_01J00000000000000000000000",
                "shop_integration_id": "shpint_1",
                "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/1",
                "sequence_order": 0,
            }
        ],
    }

    response = client.post("/api/v1/integrations/shopify/metafield-preferences", json=payload)

    assert response.status_code == 200
    assert captured["contexts"][0].incoming_data == payload
    assert response.json()["data"] == [result]


@pytest.mark.unit
def test_update_metafield_preference_sequence_order_route_forwards_target_and_position(
    monkeypatch,
) -> None:
    expected_data = {"client_id": "shpmfp_1", "sequence_order": 3}
    client, captured = _build_test_client(
        claims={"role_name": "seller", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(
            success=True,
            data=expected_data,
            error=None,
        ),
    )

    response = client.patch(
        "/api/v1/integrations/shopify/metafield-preferences/shpmfp_1",
        json={"sequence_order": 3},
    )

    assert response.status_code == 200
    assert captured["contexts"][0].incoming_data == expected_data
    assert response.json()["data"] == expected_data


@pytest.mark.unit
def test_update_metafield_preference_sequence_order_route_rejects_negative_position(
    monkeypatch,
) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "seller", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={}, error=None),
    )

    response = client.patch(
        "/api/v1/integrations/shopify/metafield-preferences/shpmfp_1",
        json={"sequence_order": -1},
    )

    assert response.status_code == 422
    assert captured["calls"] == 0


@pytest.mark.unit
def test_grouped_metafield_preference_query_route_forwards_all_query_params(monkeypatch) -> None:
    expected_data = {
        "shops": [
            {
                "shop_integration_id": "shpint_1",
                "shop_domain": "shop-a.myshopify.com",
                "item_categories": [],
                "unavailable_definition_ids": [],
                "search_results": [],
            }
        ]
    }
    client, captured = _build_test_client(
        claims={"role_name": "manager", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(
            success=True,
            data=expected_data,
            error=None,
        ),
    )

    response = client.get(
        "/api/v1/integrations/shopify/metafield-preferences",
        params={
            "shop_integration_ids": "shpint_1,shpint_2",
            "item_category_ids": "icat_1,icat_2",
            "q": "height",
            "only_my_preferences": "true",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == expected_data
    assert captured["contexts"][0].query_params == {
        "shop_integration_ids": "shpint_1,shpint_2",
        "item_category_ids": "icat_1,icat_2",
        "q": "height",
        "only_my_preferences": "true",
    }
    route_paths = [str(route.path) for route in shopify_router.router.routes]
    assert "/metafield-preferences" in route_paths
    assert "/shops/{shop_integration_id}/metafield-preferences" not in route_paths


@pytest.mark.unit
def test_batch_metafield_preference_create_route_rejects_field_role(monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "field", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data=[], error=None),
    )

    response = client.post(
        "/api/v1/integrations/shopify/metafield-preferences",
        json={"item_category_id": "icat_1", "preferences": []},
    )

    assert response.status_code == 403
    assert captured["calls"] == 0


@pytest.mark.unit
def test_grouped_metafield_preference_query_route_rejects_field_role(monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "field", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"shops": []}, error=None),
    )

    response = client.get(
        "/api/v1/integrations/shopify/metafield-preferences",
        params={"shop_integration_ids": "shpint_1"},
    )

    assert response.status_code == 403
    assert captured["calls"] == 0


@pytest.mark.unit
def test_batch_metafield_preference_delete_route_forwards_body_and_acknowledges(monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "seller", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={}, error=None),
    )
    payload = {"client_ids": ["shpmfp_1", "shpmfp_2"]}

    response = client.request(
        "DELETE",
        "/api/v1/integrations/shopify/metafield-preferences",
        json=payload,
    )

    assert response.status_code == 200
    assert captured["contexts"][0].incoming_data == payload
    assert response.json()["data"] == {}


@pytest.mark.unit
def test_batch_metafield_preference_delete_route_rejects_field_role(monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "field", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={}, error=None),
    )

    response = client.request(
        "DELETE",
        "/api/v1/integrations/shopify/metafield-preferences",
        json={"client_ids": ["shpmfp_1"]},
    )

    assert response.status_code == 403
    assert captured["calls"] == 0
