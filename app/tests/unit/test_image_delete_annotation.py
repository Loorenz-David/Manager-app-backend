from types import SimpleNamespace

import pytest

from beyo_manager.errors.not_found import NotFound
from beyo_manager.services.commands.images.delete_annotation import delete_annotation
from beyo_manager.services.context import ServiceContext


class _FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, annotation_by_id: dict[str, object]):
        self._annotation_by_id = annotation_by_id
        self.deleted = []

    def begin(self):
        return _FakeBegin()

    async def get(self, model, client_id):
        return self._annotation_by_id.get(client_id)

    async def delete(self, obj):
        self.deleted.append(obj)


@pytest.mark.unit
async def test_delete_annotation_hard_delete_success():
    annotation = SimpleNamespace(client_id="ian_1", image_id="img_1")
    session = _FakeSession({"ian_1": annotation})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1", "annotation_client_id": "ian_1"},
        session=session,
    )

    result = await delete_annotation(ctx)

    assert result == {"client_id": "ian_1", "deleted": True}
    assert session.deleted == [annotation]


@pytest.mark.unit
async def test_delete_annotation_not_found_on_missing_annotation():
    session = _FakeSession({})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1", "annotation_client_id": "ian_missing"},
        session=session,
    )

    with pytest.raises(NotFound, match="Image annotation not found"):
        await delete_annotation(ctx)


@pytest.mark.unit
async def test_delete_annotation_not_found_on_image_mismatch():
    annotation = SimpleNamespace(client_id="ian_1", image_id="img_other")
    session = _FakeSession({"ian_1": annotation})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={"image_client_id": "img_1", "annotation_client_id": "ian_1"},
        session=session,
    )

    with pytest.raises(NotFound, match="Image annotation not found"):
        await delete_annotation(ctx)
