from unittest.mock import AsyncMock, patch

import pytest

from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent
from beyo_manager.services.infra.events.handlers import socket_handler


@pytest.mark.unit
async def test_batch_workspace_event_routes_list_payload_to_workspace():
    event = BatchWorkspaceEvent(
        event_name="task:step-created",
        workspace_id="ws_1",
        items=[
            {"client_id": "tsp_1", "working_section_id": "wsec_1"},
            {"client_id": "tsp_2", "working_section_id": "wsec_2"},
        ],
    )

    with patch.object(
        socket_handler,
        "push_workspace_event_items",
        new=AsyncMock(),
    ) as push_mock:
        await socket_handler.handle(event)

    push_mock.assert_awaited_once_with(
        "ws_1",
        "task:step-created",
        [
            {"client_id": "tsp_1", "working_section_id": "wsec_1"},
            {"client_id": "tsp_2", "working_section_id": "wsec_2"},
        ],
    )
