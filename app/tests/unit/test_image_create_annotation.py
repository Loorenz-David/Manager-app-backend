from types import SimpleNamespace

import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.base.identity import generate_id
from beyo_manager.services.commands.images.create_annotation import create_annotation
from beyo_manager.services.context import ServiceContext


class _FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, image):
        self._image = image
        self.added = []

    def begin(self):
        return _FakeBegin()

    async def get(self, model, client_id):
        return self._image

    def add(self, obj):
        if not getattr(obj, "client_id", None):
            obj.client_id = generate_id(obj.CLIENT_ID_PREFIX)
        self.added.append(obj)


@pytest.mark.unit
async def test_create_annotation_single_payload_still_supported():
    image = SimpleNamespace(client_id="img_1", deleted_at=None)
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "annotation_type": "draw",
            "data": {"points": [[0, 0], [1, 1]], "color": "#ff0000"},
            "accuracy": 95,
        },
        session=session,
    )

    result = await create_annotation(ctx)

    assert "client_id" in result
    assert len(session.added) == 1
    assert session.added[0].data["color"] == "#ff0000"


@pytest.mark.unit
async def test_create_annotation_batch_returns_created_ids_list():
    image = SimpleNamespace(client_id="img_1", deleted_at=None)
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "annotation_type": "draw",
            "data": {
                "items": [
                    {"tool": "draw", "points": [[0, 0], [1, 1]], "color": "#ff0000"},
                    {"tool": "text", "x": 10, "y": 14, "text": "Note"},
                ]
            },
            "accuracy": 88,
        },
        session=session,
    )

    result = await create_annotation(ctx)

    assert "created_annotation_client_ids" in result
    assert len(result["created_annotation_client_ids"]) == 2
    assert len(session.added) == 2
    assert session.added[0].data["tool"] == "draw"
    assert session.added[1].data["tool"] == "text"


@pytest.mark.unit
async def test_create_annotation_batch_validation_includes_item_index():
    image = SimpleNamespace(client_id="img_1", deleted_at=None)
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "data": {
                "items": [
                    {"tool": "draw", "points": [[0, 0], [1, 1]], "color": "#ff0000"},
                    {"tool": "text", "x": 10, "text": "Missing y"},
                ]
            },
        },
        session=session,
    )

    with pytest.raises(ValidationError) as exc:
        await create_annotation(ctx)

    assert "items[1]" in str(exc.value)
    assert "missing required keys for text" in str(exc.value)


@pytest.mark.unit
async def test_create_annotation_batch_arrow_accepts_frontend_coordinates():
    image = SimpleNamespace(client_id="img_1", deleted_at=None)
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "annotation_type": "arrow",
            "data": {
                "items": [
                    {
                        "tool": "arrow",
                        "fromX": 0.1,
                        "fromY": 0.2,
                        "toX": 0.8,
                        "toY": 0.9,
                        "color": "#ff5a36",
                        "strokeWidth": 3,
                    }
                ]
            },
        },
        session=session,
    )

    result = await create_annotation(ctx)

    assert len(result["created_annotation_client_ids"]) == 1
    saved = session.added[0].data
    assert saved["from"] == {"x": 0.1, "y": 0.2}
    assert saved["to"] == {"x": 0.8, "y": 0.9}
