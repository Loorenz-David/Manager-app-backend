"""What a Scanner webhook delivery leaves behind in the log.

These routes used to record nothing at all — neither the body that arrived nor
the answer given — so a delivery that was rejected looked identical to one that
never happened. This file pins the three things that matter:

  1. the inbound body is logged,
  2. the per-entry outcomes are logged,
  3. the request headers are **never** logged — they carry the shared secret.

Same shape as `test_location_tracker_webhooks_router.py`: `run_service` is faked,
so nothing here touches a database.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.core.logging.formatter import StructuredJsonFormatter
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import location_tracker_webhooks as router_module

pytestmark = pytest.mark.unit

_SECRET = "super-secret-scanner-key"


def _build_test_client(monkeypatch, run_service_result):
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1/location-tracker")

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(command, ctx):
        return run_service_result

    app.dependency_overrides[get_db] = _fake_get_db
    monkeypatch.setattr(router_module, "run_service", _fake_run_service)
    return TestClient(app)


def _events(caplog):
    """The router's own records, by event type. `caplog` also catches httpx and
    anything else that logs during the request, and those have no `event_type`."""
    return {
        record.event_type: record
        for record in caplog.records
        if record.name == router_module.__name__
    }


def _post(client, body=b'[{"itemCategory":"chair"}]'):
    return client.post(
        "/api/v1/location-tracker/webhooks/stock-demand",
        content=body,
        headers={"X-API-KEY": _SECRET},
    )


def test_the_inbound_body_and_the_outcomes_are_both_logged(monkeypatch, caplog):
    client = _build_test_client(
        monkeypatch,
        SimpleNamespace(
            success=True,
            data={"results": [{"outcome": "created"}, {"outcome": "not_found"}]},
            error=None,
        ),
    )

    with caplog.at_level(logging.INFO, logger=router_module.__name__):
        assert _post(client).status_code == 200

    by_event = _events(caplog)
    assert set(by_event) == {"stock_webhook.received", "stock_webhook.completed"}

    received = by_event["stock_webhook.received"]
    assert received.webhook == "stock-demand"
    assert received.body_length == len(b'[{"itemCategory":"chair"}]')
    assert received.payload == '[{"itemCategory":"chair"}]'

    completed = by_event["stock_webhook.completed"]
    assert completed.outcomes == {"created": 1, "not_found": 1}
    assert completed.status_code == 200
    assert completed.duration_ms >= 0


def test_a_refusal_is_logged_with_its_status_instead_of_passing_silently(
    monkeypatch, caplog
):
    client = _build_test_client(
        monkeypatch,
        SimpleNamespace(
            success=False, data=None, error=LocationTrackerWebhookAuthError()
        ),
    )

    with caplog.at_level(logging.INFO, logger=router_module.__name__):
        assert _post(client).status_code == 401

    rejected = _events(caplog)["stock_webhook.rejected"]
    assert rejected.status_code == 401
    assert rejected.error == "LocationTrackerWebhookAuthError: Unauthorized."


def test_the_api_key_header_never_reaches_the_log(monkeypatch, caplog):
    """The router hands the whole header dict to the command, so it would be easy
    to log the secret by accident. Rendered output, not just the record fields."""
    client = _build_test_client(
        monkeypatch,
        SimpleNamespace(success=True, data={"results": []}, error=None),
    )

    with caplog.at_level(logging.INFO, logger=router_module.__name__):
        assert _post(client).status_code == 200

    formatter = StructuredJsonFormatter()
    rendered = "\n".join(formatter.format(record) for record in caplog.records)
    assert _SECRET not in rendered
    assert "x-api-key" not in rendered.lower()


def test_payload_logging_can_be_switched_off(monkeypatch, caplog):
    monkeypatch.setattr(
        router_module.settings, "stock_webhook_log_payloads", False, raising=True
    )
    client = _build_test_client(
        monkeypatch,
        SimpleNamespace(
            success=True, data={"results": [{"outcome": "created"}]}, error=None
        ),
    )

    with caplog.at_level(logging.INFO, logger=router_module.__name__):
        assert _post(client).status_code == 200

    by_event = _events(caplog)
    assert by_event["stock_webhook.received"].payload is None
    assert by_event["stock_webhook.completed"].results is None
    # The counts survive: they are the outcome, not the payload.
    assert by_event["stock_webhook.completed"].outcomes == {"created": 1}


def test_an_oversized_body_is_truncated_rather_than_written_whole(monkeypatch, caplog):
    body = b"x" * (router_module._MAX_LOGGED_BODY_CHARS + 500)
    client = _build_test_client(
        monkeypatch,
        SimpleNamespace(success=True, data={"results": []}, error=None),
    )

    with caplog.at_level(logging.INFO, logger=router_module.__name__):
        assert _post(client, body=body).status_code == 200

    received = _events(caplog)["stock_webhook.received"]
    assert len(received.payload) < len(body)
    assert received.payload.endswith(f"[truncated, {len(body)} chars]")
    # The true size is still recorded, so truncation never hides how big it was.
    assert received.body_length == len(body)


def test_a_body_that_is_not_valid_utf8_still_logs_instead_of_raising(
    monkeypatch, caplog
):
    client = _build_test_client(
        monkeypatch,
        SimpleNamespace(success=True, data={"results": []}, error=None),
    )

    with caplog.at_level(logging.INFO, logger=router_module.__name__):
        assert _post(client, body=b"\xff\xfe not json").status_code == 200

    received = _events(caplog)["stock_webhook.received"]
    assert "not json" in received.payload


def test_the_formatter_emits_caller_fields_instead_of_dropping_them(caplog):
    """The formatter used to keep a fixed whitelist of seven keys and silently
    drop every other `extra=`, which is why several existing log calls in this
    repo emit fields that never appear in the output."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.event_type = "stock_webhook.received"
    record.webhook = "stock-demand"
    record.outcomes = {"created": 2}

    emitted = json.loads(StructuredJsonFormatter().format(record))

    assert emitted["event_type"] == "stock_webhook.received"
    assert emitted["webhook"] == "stock-demand"
    assert emitted["outcomes"] == {"created": 2}
    # Standard LogRecord machinery must not leak into the line.
    assert "pathname" not in emitted
    assert "levelno" not in emitted


def test_the_formatter_does_not_raise_on_a_value_json_cannot_encode(caplog):
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.event_type = "x"
    record.thing = object()

    emitted = json.loads(StructuredJsonFormatter().format(record))

    assert emitted["thing"].startswith("<object object at")
