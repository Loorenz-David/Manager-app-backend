import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import items as items_router


@pytest.mark.unit
async def test_route_batch_update_item_positions_forwards_entries(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"updated_ids": ["itm_1", "itm_2"]}, error=None)

    monkeypatch.setattr(items_router, "run_service", _fake_run_service)

    result = await items_router.route_batch_update_item_positions(
        body=items_router._BatchUpdateItemPositionsBody(
            entries=[
                items_router._ItemPositionEntry(client_id="itm_1", item_position="A-01"),
                items_router._ItemPositionEntry(client_id="itm_2", item_position=None),
            ]
        ),
        claims={"user_id": "usr_1", "role_name": "manager"},
        session=object(),
    )

    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload["ok"] is True
    assert captured["command"] is items_router.batch_update_item_positions
    assert captured["ctx"].incoming_data == {
        "entries": [
            {"client_id": "itm_1", "item_position": "A-01"},
            {"client_id": "itm_2", "item_position": None},
        ]
    }
