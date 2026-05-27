from types import SimpleNamespace

import pytest

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.images import soft_delete_image as delete_image_module
from beyo_manager.services.commands.images.soft_delete_image import soft_delete_image
from beyo_manager.services.context import ServiceContext


class _FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, image):
        self._image = image
        self.flushed = 0
        self.deleted = []
        self.executed = []

    def begin(self):
        return _FakeBegin()

    async def get(self, model, client_id):
        return self._image

    async def flush(self):
        self.flushed += 1

    async def execute(self, statement):
        self.executed.append(statement)

    async def delete(self, obj):
        self.deleted.append(obj)


@pytest.mark.unit
async def test_soft_delete_image_default_sets_deleted_fields():
    image = SimpleNamespace(client_id="img_1", deleted_at=None, deleted_by_id=None)
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1"},
        session=session,
    )

    result = await soft_delete_image(ctx)

    assert result == {"client_id": "img_1"}
    assert image.deleted_at is not None
    assert image.deleted_by_id == "usr_1"
    assert session.executed == []
    assert session.deleted == []


@pytest.mark.unit
async def test_soft_delete_image_raises_when_already_deleted():
    image = SimpleNamespace(client_id="img_1", deleted_at="already", deleted_by_id="usr_2")
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1"},
        session=session,
    )

    with pytest.raises(ValidationError, match="image is already deleted"):
        await soft_delete_image(ctx)


@pytest.mark.unit
async def test_hard_delete_image_removes_graph_and_row(monkeypatch):
    class _StorageClient:
        def delete_object(self, key):
            self.key = key

    storage_client = _StorageClient()
    monkeypatch.setattr(delete_image_module, "get_storage_client", lambda: storage_client)

    image = SimpleNamespace(client_id="img_1", image_url="images/ws/item/file.webp", last_event_id="iev_1", deleted_at=None)
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1", "hard_delete": True},
        session=session,
    )

    result = await soft_delete_image(ctx)

    assert result == {"client_id": "img_1", "deleted": True, "hard_deleted": True}
    assert storage_client.key == "images/ws/item/file.webp"
    assert image.last_event_id is None
    assert session.flushed == 1
    assert [stmt.table.name for stmt in session.executed] == ["image_links", "image_annotations", "image_events"]
    assert session.deleted == [image]


@pytest.mark.unit
async def test_hard_delete_image_continues_when_storage_delete_fails(monkeypatch):
    class _StorageClient:
        def delete_object(self, key):
            raise RuntimeError("storage unavailable")

    monkeypatch.setattr(delete_image_module, "get_storage_client", lambda: _StorageClient())

    image = SimpleNamespace(client_id="img_1", image_url="images/ws/item/file.webp", last_event_id="iev_1", deleted_at=None)
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1", "hard_delete": True},
        session=session,
    )

    result = await soft_delete_image(ctx)

    assert result["hard_deleted"] is True
    assert session.deleted == [image]


@pytest.mark.unit
async def test_hard_delete_image_allows_already_soft_deleted_rows(monkeypatch):
    class _StorageClient:
        def delete_object(self, key):
            return None

    monkeypatch.setattr(delete_image_module, "get_storage_client", lambda: _StorageClient())

    image = SimpleNamespace(client_id="img_1", image_url="images/ws/item/file.webp", last_event_id="iev_1", deleted_at="already")
    session = _FakeSession(image)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1", "hard_delete": True},
        session=session,
    )

    result = await soft_delete_image(ctx)

    assert result["hard_deleted"] is True
    assert session.deleted == [image]


@pytest.mark.unit
async def test_hard_delete_image_not_found():
    session = _FakeSession(None)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_missing", "hard_delete": True},
        session=session,
    )

    with pytest.raises(NotFound, match="Image not found"):
        await soft_delete_image(ctx)
