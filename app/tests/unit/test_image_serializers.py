from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.images.serializers import serialize_image_link


@pytest.mark.unit
def test_serialize_image_link_includes_annotation_when_requested():
    annotation = SimpleNamespace(
        client_id="ian_1",
        annotation_type="draw",
        data={"points": [[0, 0], [1, 1]], "color": "#ff0000"},
        accuracy=90,
        created_at=datetime.now(timezone.utc),
    )
    annotation_2 = SimpleNamespace(
        client_id="ian_2",
        annotation_type="text",
        data={"x": 10, "y": 14, "text": "note"},
        accuracy=88,
        created_at=datetime.now(timezone.utc),
    )
    image = SimpleNamespace(
        client_id="img_1",
        image_url="https://example.com/test.webp",
        storage_provider="s3",
        source_type="uploaded",
        source_reference="s3_image_url",
        width_px=None,
        height_px=None,
        file_size_bytes=100,
        created_at=datetime.now(timezone.utc),
        last_event=None,
        image_annotations=[annotation, annotation_2],
    )
    link = SimpleNamespace(
        client_id="iml_1",
        image=image,
        entity_type="item",
        entity_client_id="item_1",
        display_order=0,
    )

    serialized = serialize_image_link(link, include_annotations=True)

    assert serialized["image"]["image_annotation"] is not None
    assert serialized["image"]["image_annotation"]["client_id"] == "ian_1"
    assert len(serialized["image"]["image_annotations"]) == 2
    assert serialized["image"]["image_annotations"][1]["client_id"] == "ian_2"
