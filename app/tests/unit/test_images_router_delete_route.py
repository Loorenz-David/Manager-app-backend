import inspect

import pytest

from beyo_manager.routers.api_v1 import images as images_router


@pytest.mark.unit
async def test_soft_delete_image_route_passes_hard_delete_true(monkeypatch):
    captured = {}

    async def _fake_run(command, data, claims, session):
        captured["command"] = command
        captured["data"] = data
        captured["claims"] = claims
        captured["session"] = session
        return {"ok": True}

    monkeypatch.setattr(images_router, "_run", _fake_run)

    claims = {"user_id": "usr_1"}
    session = object()
    result = await images_router.soft_delete_image_route("img_1", hard_delete=True, claims=claims, session=session)

    assert result == {"ok": True}
    assert captured["command"] is images_router.soft_delete_image
    assert captured["data"] == {"image_client_id": "img_1", "hard_delete": True}
    assert captured["claims"] == claims
    assert captured["session"] is session


@pytest.mark.unit
def test_soft_delete_image_route_hard_delete_default_is_false():
    signature = inspect.signature(images_router.soft_delete_image_route)
    hard_delete_default = signature.parameters["hard_delete"].default

    assert getattr(hard_delete_default, "default", None) is False
