from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.errors.base import DomainError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.routers.api_v1 import items as items_router
from beyo_manager.routers.api_v1 import tasks as tasks_router
from beyo_manager.services.commands.items.requests import (
    CreateItemRequest,
    FindOrCreateItemRequest,
    UpdateItemRequest,
)
from beyo_manager.services.commands.tasks.requests import FindOrCreateItemInput
from beyo_manager.models.database import get_db
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims


_MESSAGE = "ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint"
_SCHEMAS = (
    ("create-item", CreateItemRequest, {"article_number": "A-1"}),
    ("patch-item", UpdateItemRequest, {"client_id": "itm_1"}),
    ("find-or-create", FindOrCreateItemRequest, {"article_number": "A-1"}),
    ("create-task-nested-item", FindOrCreateItemInput, {"article_number": "A-1"}),
)
_MONEY_KEYS = ("item_value_minor", "item_cost_minor", "item_currency")
_APP_ROOT = Path(__file__).parents[2]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("schema_id", "schema", "base", "money_case"),
    [
        (schema_id, schema, base, money_case)
        for schema_id, schema, base in _SCHEMAS
        for money_case in ("absent", "present-null", "present-nonnull")
    ],
    ids=[f"{schema_id}-{money_case}" for schema_id, _, _, money_case in [
        (schema_id, schema, base, money_case)
        for schema_id, schema, base in _SCHEMAS
        for money_case in ("absent", "present-null", "present-nonnull")
    ]],
)
def test_bridge_is_reject_iff_present_and_nonnull(schema_id, schema, base, money_case):
    payload = dict(base)
    if money_case == "present-null":
        payload["item_currency"] = None
    elif money_case == "present-nonnull":
        payload["item_currency"] = "swedish_krona"

    if money_case == "present-nonnull":
        with pytest.raises(ValidationError) as exc_info:
            schema.model_validate(payload)
        assert str(exc_info.value) == _MESSAGE
    else:
        parsed = schema.model_validate(payload)
        assert getattr(parsed, "item_currency") is None


@pytest.mark.unit
@pytest.mark.parametrize("field_name", _MONEY_KEYS, ids=lambda value: f"create-item-{value}")
def test_create_item_bridge_covers_each_removed_key(field_name):
    value = "swedish_krona" if field_name == "item_currency" else 1
    with pytest.raises(ValidationError, match="^ITEM_MONEY_MOVED:"):
        CreateItemRequest.model_validate({"article_number": "A-1", field_name: value})


@pytest.mark.unit
def test_router_bodies_retain_money_keys_until_command_validator():
    item_bodies = (
        items_router._CreateItemBody,
        items_router._UpdateItemBody,
        items_router._FindOrCreateItemBody,
    )
    for body_type in item_bodies:
        body = body_type.model_validate({"item_value_minor": 17})
        assert body.model_dump()["item_value_minor"] == 17

    task_body = tasks_router._TaskItemInputBody.model_validate({"item_cost_minor": 19})
    assert task_body.model_dump()["item_cost_minor"] == 19


@pytest.mark.unit
def test_item_write_paths_and_orm_surface_no_longer_reference_legacy_columns():
    command_paths = (
        _APP_ROOT / "beyo_manager/services/commands/items/_create_item_in_session.py",
        _APP_ROOT / "beyo_manager/services/commands/items/create_item.py",
        _APP_ROOT / "beyo_manager/services/commands/items/find_or_create_item.py",
        _APP_ROOT / "beyo_manager/services/commands/items/update_item.py",
        _APP_ROOT / "beyo_manager/services/commands/tasks/create_task.py",
    )
    for path in command_paths:
        source = path.read_text()
        assert all(field_name not in source for field_name in _MONEY_KEYS)

    from beyo_manager.models.tables.items.item import Item

    assert set(_MONEY_KEYS).isdisjoint(Item.__table__.columns.keys())


@pytest.mark.unit
def test_create_task_router_preserves_nonnull_money_into_domain_validator(monkeypatch):
    app = FastAPI()
    app.include_router(tasks_router.router, prefix="/tasks")

    async def fake_get_db():
        yield object()

    async def fake_run_service(command, context):
        try:
            data = await command(context)
        except DomainError as exc:
            return SimpleNamespace(success=False, data=None, error=exc)
        return SimpleNamespace(success=True, data=data, error=None)

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": "worker",
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(tasks_router, "run_service", fake_run_service)

    response = TestClient(app).put(
        "/tasks",
        json={"task_type": "return", "item": {"item_value_minor": 17}},
    )

    assert response.status_code == 422
    assert response.json() == {"error": _MESSAGE, "ok": False}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("endpoint_id", "method", "path"),
    [
        ("create-item-router", "put", "/items"),
        ("patch-item-router", "patch", "/items/itm_1"),
        ("find-or-create-router", "post", "/items/find-or-create"),
    ],
    ids=lambda value: value if isinstance(value, str) and value.endswith("router") else None,
)
def test_item_router_surfaces_reject_present_nonnull_money(endpoint_id, method, path, monkeypatch):
    del endpoint_id
    app = FastAPI()
    app.include_router(items_router.router, prefix="/items")

    async def fake_get_db():
        yield object()

    async def fake_run_service(command, context):
        try:
            data = await command(context)
        except DomainError as exc:
            return SimpleNamespace(success=False, data=None, error=exc)
        return SimpleNamespace(success=True, data=data, error=None)

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": "manager",
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(items_router, "run_service", fake_run_service)

    response = getattr(TestClient(app), method)(path, json={"item_currency": "swedish_krona"})

    assert response.status_code == 422
    assert response.json() == {"error": _MESSAGE, "ok": False}
