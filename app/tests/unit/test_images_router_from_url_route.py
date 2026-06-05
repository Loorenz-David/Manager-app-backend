import pytest

from beyo_manager.routers.api_v1 import images as images_router


@pytest.mark.unit
async def test_create_from_url_route_accepts_top_level_list_and_wraps_items(monkeypatch):
    captured = {}

    async def _fake_run(command, data, claims, session):
        captured["command"] = command
        captured["data"] = data
        captured["claims"] = claims
        captured["session"] = session
        return {"ok": True}

    monkeypatch.setattr(images_router, "_run", _fake_run)

    claims = {"user_id": "usr_1", "role_name": "manager"}
    session = object()
    body = [
        images_router.CreateFromUrlBody(
            image_url="https://cdn.example.com/items/1.webp",
            entity_type="item",
            entity_client_id="itm_1",
            image_client_id="img_1",
            width_px=1200,
            height_px=900,
            image_annotations=[{"tool": "text", "x": 1, "y": 1, "text": "hello"}],
        ),
        images_router.CreateFromUrlBody(
            image_url="https://cdn.example.com/items/2.webp",
            entity_type="item",
            entity_client_id="itm_1",
        ),
    ]

    result = await images_router.image_create_from_url_route(body=body, claims=claims, session=session)

    assert result == {"ok": True}
    assert captured["command"] is images_router.create_from_url
    assert "items" in captured["data"]
    assert len(captured["data"]["items"]) == 2
    assert captured["data"]["items"][0]["image_client_id"] == "img_1"
    assert captured["claims"] == claims
    assert captured["session"] is session
