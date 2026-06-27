from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.domain.images.enums import ImageEventTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.base.identity import generate_id
from beyo_manager.services.commands.images import confirm_upload as confirm_upload_module
from beyo_manager.services.commands.images.confirm_upload import confirm_upload
from beyo_manager.services.context import ServiceContext


class _FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _FakeSession:
    def __init__(self, uploads_by_id: dict[str, object]):
        self._uploads_by_id = uploads_by_id
        self.added = []

    def begin(self):
        return _FakeBegin()

    async def get(self, model, client_id):
        return self._uploads_by_id.get(client_id)

    def add(self, obj):
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)
        if not getattr(obj, "client_id", None):
            obj.client_id = generate_id(obj.CLIENT_ID_PREFIX)
        self.added.append(obj)

    async def flush(self):
        return None

    async def execute(self, statement):
        return _FakeScalarResult(0)


def _build_upload(client_id: str, storage_key: str):
    return SimpleNamespace(
        client_id=client_id,
        storage_key=storage_key,
        status=PendingUploadStatusEnum.PENDING,
        size_bytes=None,
    )


@pytest.mark.unit
async def test_confirm_upload_single_accepts_optimistic_id_dimensions_and_annotations(monkeypatch):
    monkeypatch.setattr(confirm_upload_module.settings, "storage_provider", "local")
    monkeypatch.setattr(
        confirm_upload_module,
        "get_storage_client",
        lambda: SimpleNamespace(head_object=lambda _key: {"content_length": 2048}),
    )

    upload = _build_upload("pu_1", "images/ws/item/a.webp")
    session = _FakeSession({"pu_1": upload})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "pending_upload_client_id": "pu_1",
            "entity_type": "item",
            "entity_client_id": "itm_1",
            "image_client_id": "img_custom_1",
            "width_px": 1600,
            "height_px": 900,
            "image_annotations": [
                {"tool": "text", "x": 10, "y": 20, "text": "Door scratch"},
                {"tool": "rectangle", "x": 1, "y": 2, "w": 10, "h": 12},
            ],
        },
        session=session,
    )

    result = await confirm_upload(ctx)

    assert result["image"]["client_id"] == "img_custom_1"
    assert result["image"]["width_px"] == 1600
    assert result["image"]["height_px"] == 900
    assert upload.status == PendingUploadStatusEnum.CONFIRMED
    assert upload.size_bytes == 2048

    annotation_rows = [obj for obj in session.added if obj.__class__.__name__ == "ImageAnnotation"]
    assert len(annotation_rows) == 2


@pytest.mark.unit
async def test_confirm_upload_batch_returns_images_array(monkeypatch):
    monkeypatch.setattr(confirm_upload_module.settings, "storage_provider", "local")
    monkeypatch.setattr(
        confirm_upload_module,
        "get_storage_client",
        lambda: SimpleNamespace(head_object=lambda _key: {"content_length": 512}),
    )

    upload_1 = _build_upload("pu_1", "images/ws/item/1.webp")
    upload_2 = _build_upload("pu_2", "images/ws/item/2.webp")
    session = _FakeSession({"pu_1": upload_1, "pu_2": upload_2})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "items": [
                {
                    "pending_upload_client_id": "pu_1",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_batch_1",
                },
                {
                    "pending_upload_client_id": "pu_2",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_batch_2",
                },
            ]
        },
        session=session,
    )

    result = await confirm_upload(ctx)

    assert "images" in result
    assert len(result["images"]) == 2
    assert {img["client_id"] for img in result["images"]} == {"img_batch_1", "img_batch_2"}
    assert upload_1.status == PendingUploadStatusEnum.CONFIRMED
    assert upload_2.status == PendingUploadStatusEnum.CONFIRMED


@pytest.mark.unit
async def test_confirm_upload_batch_rejects_duplicate_image_ids(monkeypatch):
    monkeypatch.setattr(confirm_upload_module.settings, "storage_provider", "local")
    monkeypatch.setattr(
        confirm_upload_module,
        "get_storage_client",
        lambda: SimpleNamespace(head_object=lambda _key: {"content_length": 512}),
    )

    upload_1 = _build_upload("pu_1", "images/ws/item/1.webp")
    upload_2 = _build_upload("pu_2", "images/ws/item/2.webp")
    session = _FakeSession({"pu_1": upload_1, "pu_2": upload_2})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "items": [
                {
                    "pending_upload_client_id": "pu_1",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_duplicate",
                },
                {
                    "pending_upload_client_id": "pu_2",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_duplicate",
                },
            ]
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="duplicate image_client_id in items"):
        await confirm_upload(ctx)


@pytest.mark.unit
async def test_confirm_upload_rejects_non_positive_dimensions(monkeypatch):
    monkeypatch.setattr(confirm_upload_module.settings, "storage_provider", "local")
    monkeypatch.setattr(
        confirm_upload_module,
        "get_storage_client",
        lambda: SimpleNamespace(head_object=lambda _key: {"content_length": 2048}),
    )

    upload = _build_upload("pu_1", "images/ws/item/a.webp")
    session = _FakeSession({"pu_1": upload})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "pending_upload_client_id": "pu_1",
            "entity_type": "item",
            "entity_client_id": "itm_1",
            "width_px": 0,
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="width_px must be a positive integer"):
        await confirm_upload(ctx)


@pytest.mark.unit
async def test_confirm_upload_note_entity_emits_note_image_event(monkeypatch):
    monkeypatch.setattr(confirm_upload_module.settings, "storage_provider", "local")
    monkeypatch.setattr(
        confirm_upload_module,
        "get_storage_client",
        lambda: SimpleNamespace(head_object=lambda _key: {"content_length": 1024}),
    )

    upload = _build_upload("pu_note_1", "images/ws/notes/a.webp")
    session = _FakeSession({"pu_note_1": upload})
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "pending_upload_client_id": "pu_note_1",
            "entity_type": "note",
            "entity_client_id": "tno_1",
        },
        session=session,
    )

    result = await confirm_upload(ctx)

    assert result["image"]["client_id"].startswith("img_")
    event_row = next(obj for obj in session.added if obj.__class__.__name__ == "ImageEvent")
    assert event_row.type == ImageEventTypeEnum.UPLOAD_NOTE_IMAGE
