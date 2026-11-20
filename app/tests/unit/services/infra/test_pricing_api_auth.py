"""`verify_pricing_api_request`: the pricing app's shared-key check."""

import logging

import pytest

from beyo_manager.config import settings
from beyo_manager.errors.permissions import PricingApiAuthError
from beyo_manager.services.infra.pricing_api.auth import verify_pricing_api_request

pytestmark = pytest.mark.unit


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", "k")
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", "ws_configured")


def test_returns_the_configured_workspace_id_on_success(configured):
    assert verify_pricing_api_request({"x-api-key": "k"}) == "ws_configured"


@pytest.mark.parametrize(
    ("headers", "cause"),
    [
        ({}, "missing_x_api_key_header"),
        ({"x-api-key": "wrong"}, "x_api_key_mismatch"),
        ({"x-api-key": "kø"}, "x_api_key_mismatch"),
    ],
    ids=["missing", "wrong", "non-ascii"],
)
def test_refuses_bad_keys_with_one_body_and_logs_the_cause(configured, caplog, headers, cause):
    with caplog.at_level(logging.WARNING), pytest.raises(PricingApiAuthError) as refused:
        verify_pricing_api_request(headers)

    assert refused.value.http_status == 401
    assert refused.value.message == "Unauthorized."
    record = next(r for r in caplog.records if getattr(r, "event_type", None) == "pricing_api.auth_refused")
    assert record.cause == cause
    assert "wrong" not in caplog.text


@pytest.mark.parametrize(
    ("setting", "cause"),
    [
        ("manager_api_key_to_location_tracker_app", "server_api_key_not_configured"),
        ("location_tracker_webhook_workspace_id", "server_workspace_id_not_configured"),
    ],
)
@pytest.mark.parametrize("blank", [None, "  "])
def test_refuses_when_the_server_is_not_configured(configured, monkeypatch, caplog, setting, cause, blank):
    monkeypatch.setattr(settings, setting, blank)

    with caplog.at_level(logging.WARNING), pytest.raises(PricingApiAuthError) as refused:
        verify_pricing_api_request({"x-api-key": "k"})

    assert refused.value.message == "Unauthorized."
    record = next(r for r in caplog.records if getattr(r, "event_type", None) == "pricing_api.auth_refused")
    assert record.cause == cause
