from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.tasks.serializers import serialize_shopify_event_flow_record


def _event(**overrides) -> SimpleNamespace:
    base = dict(
        client_id="shpevt_1",
        shop_integration_id="shpint_1",
        event_type=SimpleNamespace(value="preorder"),
        severity=SimpleNamespace(value="info"),
        message="Shopify pre-order product created.",
        created_at=datetime(2026, 7, 27, 10, 15, tzinfo=timezone.utc),
        created_by_id="usr_1",
        metadata_json={
            "task_id": "tsk_1",
            "preorder_operation_id": "shpsi_1",
            "status": "succeeded",
            "requested_operation": "create",
            "shopify_product_id": "gid://shopify/Product/1",
            "error_code": None,
        },
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.unit
def test_matches_the_shared_flow_record_shape() -> None:
    # Every flow record carries these six keys regardless of source, so the frontend can render a
    # mixed feed without branching first.
    result = serialize_shopify_event_flow_record(_event(), {})

    for key in ("type", "entity_type", "entity_client_id", "description", "created_at", "created_by"):
        assert key in result
    assert result["type"] == "shopify_event"
    assert result["entity_type"] == "shopify_integration_event"


@pytest.mark.unit
def test_description_is_the_event_message_verbatim() -> None:
    result = serialize_shopify_event_flow_record(
        _event(message="Shopify pre-order product provisioning enqueued."), {}
    )

    assert result["description"] == "Shopify pre-order product provisioning enqueued."


@pytest.mark.unit
def test_entity_client_id_is_the_preorder_operation_for_socket_correlation() -> None:
    # Matches `preorder_operation_id` in the shopify.preorder.processed socket payload.
    result = serialize_shopify_event_flow_record(_event(), {})

    assert result["entity_client_id"] == "shpsi_1"


@pytest.mark.unit
def test_entity_client_id_falls_back_to_the_event_id() -> None:
    result = serialize_shopify_event_flow_record(_event(metadata_json={"task_id": "tsk_1"}), {})

    assert result["entity_client_id"] == "shpevt_1"


@pytest.mark.unit
def test_missing_metadata_does_not_raise() -> None:
    result = serialize_shopify_event_flow_record(_event(metadata_json=None), {})

    assert result["entity_client_id"] == "shpevt_1"
    assert result["status"] is None
    assert result["error_code"] is None
    assert result["shopify_product_id"] is None


@pytest.mark.unit
def test_failure_event_surfaces_severity_and_error_code() -> None:
    result = serialize_shopify_event_flow_record(
        _event(
            severity=SimpleNamespace(value="error"),
            message="Shopify pre-order product failed: ambiguous_product_match.",
            metadata_json={
                "task_id": "tsk_1",
                "preorder_operation_id": "shpsi_1",
                "status": "failed",
                "error_code": "ambiguous_product_match",
                "shopify_product_id": None,
            },
        ),
        {},
    )

    assert result["severity"] == "error"
    assert result["status"] == "failed"
    assert result["error_code"] == "ambiguous_product_match"


@pytest.mark.unit
def test_resolves_the_creating_user_when_known() -> None:
    users_map = {
        "usr_1": SimpleNamespace(client_id="usr_1", username="dlorenz", profile_picture=None)
    }

    result = serialize_shopify_event_flow_record(_event(), users_map)

    assert result["created_by"] == {
        "client_id": "usr_1",
        "username": "dlorenz",
        "profile_picture": None,
    }


@pytest.mark.unit
def test_unknown_user_still_yields_a_stub_with_the_id() -> None:
    # Same fallback the history and step records use when the user row isn't loaded.
    result = serialize_shopify_event_flow_record(_event(), {})

    assert result["created_by"]["client_id"] == "usr_1"


@pytest.mark.unit
def test_created_by_is_null_when_the_event_has_no_creator() -> None:
    # Worker-raised events can legitimately have no user attached; `None` is the shared contract,
    # matching serialize_history_flow_record.
    result = serialize_shopify_event_flow_record(_event(created_by_id=None), {})

    assert result["created_by"] is None


@pytest.mark.unit
def test_carries_no_customer_data_or_credentials() -> None:
    # The events this reads are built from IDs, a status and an error code only. Guard against a
    # future metadata key leaking through into a task-visible feed.
    result = serialize_shopify_event_flow_record(_event(), {})

    forbidden = {"access_token", "token", "email", "phone", "address", "customer", "raw_payload"}
    assert forbidden.isdisjoint(result.keys())
