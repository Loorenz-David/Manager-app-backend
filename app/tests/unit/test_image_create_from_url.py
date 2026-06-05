from datetime import datetime, timezone

import pytest

from beyo_manager.domain.images.enums import ImageEventTypeEnum, ImageSourceTypeEnum, ImageStorageProviderEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.base.identity import generate_id
from beyo_manager.services.commands.images.create_from_url import create_from_url
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
    def __init__(self, existing_count: int = 0):
        self._existing_count = existing_count
        self.added = []

    def begin(self):
        return _FakeBegin()

    def add(self, obj):
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)
        if not getattr(obj, "client_id", None):
            obj.client_id = generate_id(obj.CLIENT_ID_PREFIX)
        self.added.append(obj)

    async def flush(self):
        return None

    async def execute(self, statement):
        return _FakeScalarResult(self._existing_count)


@pytest.mark.unit
async def test_create_from_url_single_creates_external_image_event_link_and_annotation():
    session = _FakeSession(existing_count=3)
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_url": "https://cdn.example.com/items/a.webp",
            "entity_type": "item",
            "entity_client_id": "itm_1",
            "image_client_id": "img_external_1",
            "width_px": 1600,
            "height_px": 900,
            "image_annotations": [
                {"tool": "text", "x": 10, "y": 20, "text": "Existing damage"},
            ],
        },
        session=session,
    )

    result = await create_from_url(ctx)

    image_payload = result["image"]
    assert image_payload["client_id"] == "img_external_1"
    assert image_payload["image_url"] == "https://cdn.example.com/items/a.webp"
    assert image_payload["storage_provider"] == ImageStorageProviderEnum.EXTERNAL.value
    assert image_payload["source_type"] == ImageSourceTypeEnum.EXTERNAL_URL.value
    assert image_payload["image_annotation"]["annotation_type"] == "text"
    assert image_payload["last_event"]["event_type"] == ImageEventTypeEnum.LINK_EXTERNAL_IMAGE.value

    link_row = next(obj for obj in session.added if obj.__class__.__name__ == "ImageLink")
    assert link_row.display_order == 3


@pytest.mark.unit
async def test_create_from_url_batch_rejects_duplicate_image_ids():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "items": [
                {
                    "image_url": "https://cdn.example.com/items/1.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_duplicate",
                },
                {
                    "image_url": "https://cdn.example.com/items/2.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_duplicate",
                },
            ]
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="duplicate image_client_id in items"):
        await create_from_url(ctx)


@pytest.mark.unit
async def test_create_from_url_rejects_non_absolute_url():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_url": "cdn.example.com/items/1.webp",
            "entity_type": "item",
            "entity_client_id": "itm_1",
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="image_url must be an absolute URL"):
        await create_from_url(ctx)


@pytest.mark.unit
async def test_create_from_url_batch_returns_images_array():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "items": [
                {
                    "image_url": "https://cdn.example.com/items/1.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_batch_1",
                },
                {
                    "image_url": "https://cdn.example.com/items/2.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_batch_2",
                },
            ]
        },
        session=session,
    )

    result = await create_from_url(ctx)

    assert "images" in result
    assert len(result["images"]) == 2
    assert {img["client_id"] for img in result["images"]} == {"img_batch_1", "img_batch_2"}


@pytest.mark.unit
async def test_create_from_url_rejects_unknown_entity_type():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_url": "https://cdn.example.com/items/1.webp",
            "entity_type": "unknown_entity",
            "entity_client_id": "itm_1",
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="entity_type must be one of"):
        await create_from_url(ctx)


@pytest.mark.unit
async def test_create_from_url_empty_annotations_list_creates_no_annotations():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_url": "https://cdn.example.com/items/1.webp",
            "entity_type": "item",
            "entity_client_id": "itm_1",
            "image_annotations": [],
        },
        session=session,
    )

    result = await create_from_url(ctx)

    annotation_rows = [obj for obj in session.added if obj.__class__.__name__ == "ImageAnnotation"]
    assert annotation_rows == []
    assert result["image"]["image_annotation"] is None


@pytest.mark.unit
async def test_create_from_url_rejects_invalid_annotation_type():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_url": "https://cdn.example.com/items/1.webp",
            "entity_type": "item",
            "entity_client_id": "itm_1",
            "image_annotations": [{"annotation_type": "laser_beam", "x": 0, "y": 0}],
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="annotation_type must be one of"):
        await create_from_url(ctx)


@pytest.mark.unit
async def test_create_from_url_batch_invalid_annotation_raises_before_any_db_write():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "items": [
                {
                    "image_url": "https://cdn.example.com/items/1.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_annotations": [{"annotation_type": "text", "x": 0, "y": 0, "text": "ok"}],
                },
                {
                    "image_url": "https://cdn.example.com/items/2.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_annotations": [{"annotation_type": "bad_type", "x": 0, "y": 0}],
                },
            ]
        },
        session=session,
    )

    with pytest.raises(ValidationError, match="annotation_type must be one of"):
        await create_from_url(ctx)

    assert session.added == []


@pytest.mark.unit
async def test_create_from_url_accepts_annotation_type_key():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_url": "https://cdn.example.com/items/1.webp",
            "entity_type": "item",
            "entity_client_id": "itm_1",
            "image_annotations": [{"annotation_type": "text", "x": 5, "y": 10, "text": "scratch"}],
        },
        session=session,
    )

    result = await create_from_url(ctx)

    annotation_rows = [obj for obj in session.added if obj.__class__.__name__ == "ImageAnnotation"]
    assert len(annotation_rows) == 1
    assert annotation_rows[0].annotation_type.value == "text"
    assert result["image"]["image_annotation"]["annotation_type"] == "text"


@pytest.mark.unit
async def test_create_from_url_annotation_accuracy_is_stored():
    session = _FakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "image_url": "https://cdn.example.com/items/1.webp",
            "entity_type": "item",
            "entity_client_id": "itm_1",
            "image_annotations": [{"annotation_type": "text", "x": 0, "y": 0, "text": "AI label", "accuracy": 87}],
        },
        session=session,
    )

    await create_from_url(ctx)

    annotation_rows = [obj for obj in session.added if obj.__class__.__name__ == "ImageAnnotation"]
    assert annotation_rows[0].accuracy == 87


class _TrackingFakeSession(_FakeSession):
    """Fake session whose execute() counts already-added ImageLink objects,
    giving correct sequential display_order in batch tests."""

    async def execute(self, statement):
        link_count = sum(1 for obj in self.added if obj.__class__.__name__ == "ImageLink")
        return _FakeScalarResult(link_count)


@pytest.mark.unit
async def test_create_from_url_batch_assigns_sequential_display_order():
    session = _TrackingFakeSession()
    ctx = ServiceContext(
        identity={"user_id": "usr_1"},
        incoming_data={
            "items": [
                {
                    "image_url": "https://cdn.example.com/items/1.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_order_1",
                },
                {
                    "image_url": "https://cdn.example.com/items/2.webp",
                    "entity_type": "item",
                    "entity_client_id": "itm_1",
                    "image_client_id": "img_order_2",
                },
            ]
        },
        session=session,
    )

    await create_from_url(ctx)

    link_rows = [obj for obj in session.added if obj.__class__.__name__ == "ImageLink"]
    assert len(link_rows) == 2
    orders = {link.image_id: link.display_order for link in link_rows}
    assert orders["img_order_1"] == 0
    assert orders["img_order_2"] == 1
