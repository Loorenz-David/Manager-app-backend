from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from beyo_manager.services.infra.storage.local_client import LocalStorageClient
from beyo_manager.services.infra.storage.s3_client import S3Client


@pytest.mark.unit
def test_local_public_url_uses_override_without_presigning(tmp_path) -> None:
    client = LocalStorageClient(
        base_path=str(tmp_path),
        host="http://localhost:8000",
        public_base_url="https://cdn.example.com/assets/",
    )

    assert client.public_url("/products/chair.webp") == (
        "https://cdn.example.com/assets/products/chair.webp"
    )


@pytest.mark.unit
def test_local_public_url_defaults_to_dev_storage_route(tmp_path) -> None:
    client = LocalStorageClient(
        base_path=str(tmp_path),
        host="http://localhost:8000/",
    )

    assert client.public_url("products/chair.webp") == (
        "http://localhost:8000/dev/storage/get/products/chair.webp"
    )


@pytest.mark.unit
def test_s3_public_url_uses_bucket_region_and_url_encodes_key(monkeypatch) -> None:
    monkeypatch.setattr("boto3.Session", MagicMock())
    client = S3Client(bucket="public-bucket", region="eu-north-1")

    assert client.public_url("products/Oak chair.webp") == (
        "https://public-bucket.s3.eu-north-1.amazonaws.com/products/Oak%20chair.webp"
    )


@pytest.mark.unit
def test_s3_public_url_honours_base_url_override(monkeypatch) -> None:
    monkeypatch.setattr("boto3.Session", MagicMock())
    client = S3Client(
        bucket="public-bucket",
        region="eu-north-1",
        public_base_url="https://cdn.example.com/shopify/",
    )

    assert client.public_url("products/chair.webp") == (
        "https://cdn.example.com/shopify/products/chair.webp"
    )
