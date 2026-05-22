from types import SimpleNamespace

import pytest

from beyo_manager.domain.images.enums import ImageAnnotationTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.images.update_annotation import update_annotation
from beyo_manager.services.context import ServiceContext


class _FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, annotation_by_id: dict[str, object]):
        self._annotation_by_id = annotation_by_id

    def begin(self):
        return _FakeBegin()

    async def get(self, model, client_id):
        return self._annotation_by_id.get(client_id)


@pytest.mark.unit
async def test_update_annotation_success_replaces_data():
    annotation = SimpleNamespace(
        client_id="ian_1",
        image_id="img_1",
        annotation_type=ImageAnnotationTypeEnum.TEXT,
        data={"x": 1, "y": 1, "text": "old"},
        accuracy=50,
    )
    session = _FakeSession({"ian_1": annotation})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "annotation_client_id": "ian_1",
            "data": {"x": 10, "y": 20, "text": "new"},
            "accuracy": 91,
        },
        session=session,
    )

    result = await update_annotation(ctx)

    assert result == {"client_id": "ian_1", "updated": True}
    assert annotation.data["text"] == "new"
    assert annotation.accuracy == 91


@pytest.mark.unit
async def test_update_annotation_arrow_accepts_frontend_coordinates():
    annotation = SimpleNamespace(
        client_id="ian_1",
        image_id="img_1",
        annotation_type=ImageAnnotationTypeEnum.ARROW,
        data={"from": {"x": 0.0, "y": 0.0}, "to": {"x": 1.0, "y": 1.0}},
        accuracy=None,
    )
    session = _FakeSession({"ian_1": annotation})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "annotation_client_id": "ian_1",
            "data": {"fromX": 0.2, "fromY": 0.3, "toX": 0.8, "toY": 0.9, "tool": "arrow"},
        },
        session=session,
    )

    await update_annotation(ctx)

    assert annotation.data["from"] == {"x": 0.2, "y": 0.3}
    assert annotation.data["to"] == {"x": 0.8, "y": 0.9}


@pytest.mark.unit
async def test_update_annotation_not_found_on_image_mismatch():
    annotation = SimpleNamespace(
        client_id="ian_1",
        image_id="img_other",
        annotation_type=ImageAnnotationTypeEnum.TEXT,
        data={"x": 1, "y": 1, "text": "old"},
        accuracy=50,
    )
    session = _FakeSession({"ian_1": annotation})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "annotation_client_id": "ian_1",
            "data": {"x": 10, "y": 20, "text": "new"},
        },
        session=session,
    )

    with pytest.raises(NotFound, match="Image annotation not found"):
        await update_annotation(ctx)


@pytest.mark.unit
async def test_update_annotation_validation_for_missing_required_fields():
    annotation = SimpleNamespace(
        client_id="ian_1",
        image_id="img_1",
        annotation_type=ImageAnnotationTypeEnum.TEXT,
        data={"x": 1, "y": 1, "text": "old"},
        accuracy=50,
    )
    session = _FakeSession({"ian_1": annotation})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_client_id": "img_1",
            "annotation_client_id": "ian_1",
            "data": {"x": 10},
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="missing required keys for text"):
        await update_annotation(ctx)
