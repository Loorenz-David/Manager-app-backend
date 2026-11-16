"""A request-validation 422 is logged by field, never by value, and answers exactly as before.

Production 2026-11-16: eleven pre-order creations failed with 422 and the logs said only
`"PUT /api/v1/tasks" 422` — the missing field (`shopify_preorder.product.price`) had to be
inferred from response sizes.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from beyo_manager.routers.api_v1.tasks import _CreateTaskBody
from beyo_manager.routers.http.validation_logging import (
    MAX_LOGGED_FIELDS,
    log_request_validation_error,
)

pytestmark = pytest.mark.unit

LOGGER = "beyo_manager.routers.http.validation_logging"

# Personal data a real pre-order carries; none of it may reach the log.
EMAIL = "a.person@example.com"
PHONE = "+46777777070"
NAME = "Cecilia Example"
NOTE = "Deliver to the back door"


def _app(*, with_handler: bool) -> FastAPI:
    app = FastAPI()
    if with_handler:
        app.add_exception_handler(RequestValidationError, log_request_validation_error)

    @app.put("/api/v1/tasks")
    def create(body: _CreateTaskBody, lookup: str | None = Query(None), limit: int = Query(10)):
        return {"ok": True}

    return app


def _preorder_missing_price() -> dict:
    return {
        "task_type": "pre_order",
        "customer_display_name": NAME,
        "primary_email": EMAIL,
        "primary_phone_number": PHONE,
        "shopify_preorder": {
            "shop_integration_id": "ssi_1",
            "product": {"tags": ["preorder"], "description": NOTE},
            "inventory": [{"location_id": "loc_1", "quantity": 1}],
        },
    }


def _validation_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if getattr(r, "event_type", None) == "request.validation_error"]


def test_logs_the_missing_price_field_and_path(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    response = TestClient(_app(with_handler=True)).put(
        f"/api/v1/tasks?lookup={EMAIL}", json=_preorder_missing_price()
    )

    assert response.status_code == 422
    [record] = _validation_records(caplog)
    assert record.method == "PUT"
    assert record.path == "/api/v1/tasks"
    assert record.error_count == 1
    assert record.fields == [{"loc": "body.shopify_preorder.product.price", "type": "missing"}]
    assert "body.shopify_preorder.product.price (missing)" in record.getMessage()


def test_never_logs_submitted_values_or_the_query_string(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    body = _preorder_missing_price()
    body["shopify_preorder"]["inventory"][0]["quantity"] = f"not-a-number {PHONE}"
    TestClient(_app(with_handler=True)).put(f"/api/v1/tasks?lookup={EMAIL}", json=body)

    [record] = _validation_records(caplog)
    logged = record.getMessage() + repr(record.__dict__)
    for value in (EMAIL, PHONE, NAME, NOTE, "not-a-number"):
        assert value not in logged
    assert {"loc": "body.shopify_preorder.inventory.0.quantity", "type": "int_parsing"} in record.fields


def test_response_is_unchanged_by_the_handler():
    body = _preorder_missing_price()
    with_handler = TestClient(_app(with_handler=True)).put("/api/v1/tasks", json=body)
    without = TestClient(_app(with_handler=False)).put("/api/v1/tasks", json=body)

    assert with_handler.status_code == without.status_code == 422
    assert with_handler.json() == without.json()


def test_caps_the_logged_fields_and_counts_the_rest(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    body = {
        "task_type": "pre_order",
        "item_issues": [{"wrong": i} for i in range(MAX_LOGGED_FIELDS + 5)],
    }
    TestClient(_app(with_handler=True)).put("/api/v1/tasks", json=body)

    [record] = _validation_records(caplog)
    assert len(record.fields) == MAX_LOGGED_FIELDS
    assert record.error_count > MAX_LOGGED_FIELDS
    assert f"(+{record.error_count - MAX_LOGGED_FIELDS} more)" in record.getMessage()


def test_a_valid_request_logs_nothing(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    response = TestClient(_app(with_handler=True)).put("/api/v1/tasks", json={"task_type": "pre_order"})

    assert response.status_code == 200
    assert _validation_records(caplog) == []


def test_the_real_app_registers_the_handler():
    from beyo_manager import create_app

    assert create_app().exception_handlers[RequestValidationError] is log_request_validation_error
