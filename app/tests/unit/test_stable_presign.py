"""Regression tests for byte-stable presigned GET URLs.

StableS3SigV4QueryAuth.add_auth mirrors botocore internals, so these tests are the
tripwire for a botocore upgrade that changes the signing path.
"""

import re
import time

import pytest

from beyo_manager.services.infra.storage import stable_presign
from beyo_manager.services.infra.storage.s3_client import S3Client

_TTL = 86400


def _client() -> S3Client:
    return S3Client(
        bucket="test-bucket",
        region="eu-north-1",
        access_key="AKIAEXAMPLE",
        secret_key="secret",
        endpoint_url="https://s3.eu-north-1.amazonaws.com",
    )


def _amz_date(url: str) -> str:
    return re.search(r"X-Amz-Date=([^&]+)", url).group(1)


@pytest.mark.unit
def test_repeated_get_urls_are_byte_identical():
    client = _client()
    first = client.generate_presigned_get_url("images/a.webp", _TTL)
    time.sleep(1.1)  # long enough that an unquantised X-Amz-Date would differ
    assert client.generate_presigned_get_url("images/a.webp", _TTL) == first


@pytest.mark.unit
def test_get_urls_are_sigv4_and_distinct_per_key():
    client = _client()
    first = client.generate_presigned_get_url("images/a.webp", _TTL)
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in first
    assert client.generate_presigned_get_url("images/b.webp", _TTL) != first


@pytest.mark.unit
def test_upload_urls_are_not_backdated():
    """Quantising must not leak into PUT — a backdated 15min upload URL would be dead."""
    client = _client()
    first = client.generate_presigned_put_url("images/a.webp", "image/webp", 900)
    time.sleep(1.1)
    second = client.generate_presigned_put_url("images/a.webp", "image/webp", 900)
    assert first != second
    assert _amz_date(first) != _amz_date(second)


@pytest.mark.unit
def test_signature_is_backdated_not_postdated():
    client = _client()
    url = client.generate_presigned_get_url("images/a.webp", _TTL)
    signed = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    assert _amz_date(url) <= signed


@pytest.mark.unit
def test_remaining_validity_never_drops_below_three_quarters_of_ttl():
    remaining = stable_presign.remaining_seconds("images/a.webp", _TTL)
    assert _TTL * 0.75 <= remaining <= _TTL


@pytest.mark.unit
@pytest.mark.parametrize("expires_in", [900, 3600, 86400])
def test_bucket_width_is_capped_at_a_quarter_of_ttl(expires_in):
    assert stable_presign.bucket_seconds(expires_in) <= max(
        stable_presign.MIN_BUCKET_SECONDS, expires_in // 4
    )


@pytest.mark.unit
def test_url_rotates_at_the_next_bucket_boundary():
    key = "images/a.webp"
    now = time.time()
    width = stable_presign.bucket_seconds(_TTL)
    assert stable_presign.bucket_start(key, _TTL, now=now) != stable_presign.bucket_start(
        key, _TTL, now=now + width
    )


@pytest.mark.unit
def test_key_offset_is_stable_across_processes():
    """blake2b, not the salted builtin hash() — workers must agree on the offset."""
    assert stable_presign._key_offset("images/a.webp", 21600) == 15826


@pytest.mark.unit
def test_offsets_spread_rotations_across_the_window():
    width = stable_presign.bucket_seconds(_TTL)
    offsets = {stable_presign._key_offset(f"images/{i}.webp", width) for i in range(500)}
    assert len(offsets) > 400  # not all clustered on one boundary
