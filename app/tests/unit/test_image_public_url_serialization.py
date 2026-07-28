"""Item images serialize to stable unsigned URLs; every other image type stays presigned."""

from types import SimpleNamespace

import pytest

from beyo_manager.domain.images import serializers as image_serializers


class _FakeStorage:
    def __init__(self) -> None:
        self.presigned_calls: list[tuple[str, int]] = []
        self.public_calls: list[str] = []

    def generate_presigned_get_url(self, key: str, expires_in: int) -> str:
        self.presigned_calls.append((key, expires_in))
        return f"https://bucket.s3.amazonaws.com/{key}?X-Amz-Signature=abc"

    def public_url(self, key: str) -> str:
        self.public_calls.append(key)
        return f"https://bucket.s3.amazonaws.com/{key}"


@pytest.fixture
def storage(monkeypatch) -> _FakeStorage:
    fake = _FakeStorage()
    monkeypatch.setattr(image_serializers, "get_storage_client", lambda: fake)
    return fake


def _image(**overrides) -> SimpleNamespace:
    base = dict(
        client_id="img_1",
        image_url="images/ws_1/item/itm_1/photo.webp",
        is_public=False,
        storage_provider=SimpleNamespace(value="s3"),
        source_type=SimpleNamespace(value="uploaded"),
        source_reference=SimpleNamespace(value="s3_image_url"),
        width_px=2000,
        height_px=1500,
        file_size_bytes=812345,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.unit
def test_public_image_is_not_presigned(storage) -> None:
    result = image_serializers.serialize_image_light(_image(is_public=True))

    assert "X-Amz-Signature" not in result["image_url"]
    assert storage.public_calls == ["images/ws_1/item/itm_1/photo.webp"]
    assert storage.presigned_calls == []


@pytest.mark.unit
def test_private_image_is_still_presigned(storage) -> None:
    result = image_serializers.serialize_image_light(_image(is_public=False))

    assert "X-Amz-Signature" in result["image_url"]
    assert storage.public_calls == []
    assert storage.presigned_calls == [("images/ws_1/item/itm_1/photo.webp", 86400)]


@pytest.mark.unit
def test_full_serializer_honours_the_flag_too(storage) -> None:
    # Both serializers must agree — a list response and a detail response for the same image
    # cannot disagree about whether the URL expires.
    from datetime import datetime, timezone

    image = _image(is_public=True, created_at=datetime(2026, 7, 28, tzinfo=timezone.utc))
    result = image_serializers.serialize_image(image)

    assert "X-Amz-Signature" not in result["image_url"]
    assert storage.presigned_calls == []


@pytest.mark.unit
def test_absolute_urls_bypass_both_paths(storage) -> None:
    # EXTERNAL / Shopify images already hold a real URL; neither signing nor composing applies.
    result = image_serializers.serialize_image_light(
        _image(image_url="https://cdn.example.com/a.jpg", is_public=True)
    )

    assert result["image_url"] == "https://cdn.example.com/a.jpg"
    assert storage.public_calls == []
    assert storage.presigned_calls == []


@pytest.mark.unit
def test_missing_flag_defaults_to_presigned(storage) -> None:
    # Defensive: a stand-in or a partially-loaded row must not silently become public.
    image = _image()
    del image.is_public

    result = image_serializers.serialize_image_light(image)

    assert "X-Amz-Signature" in result["image_url"]
    assert storage.public_calls == []
