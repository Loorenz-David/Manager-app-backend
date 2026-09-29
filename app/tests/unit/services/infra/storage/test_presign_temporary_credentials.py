"""Presigned GET URLs signed with temporary credentials (an EC2 instance role).

A URL signed with temporary credentials stops working when they expire, whatever its
X-Amz-Expires says. These tests pin that a URL is never stated, or served from the
signing cache, as valid beyond the credentials that signed it.

They also guard the botocore internal `S3Client._credential_window` reads
(`RefreshableCredentials._expiry_time`), which botocore does not expose publicly.
"""

from __future__ import annotations

import datetime as dt
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import botocore.session
import pytest
from botocore.credentials import ReadOnlyCredentials, RefreshableCredentials

from beyo_manager.services.infra.storage import stable_presign
from beyo_manager.services.infra.storage.s3_client import S3Client
from beyo_manager.services.queries.images import get_download_url as get_download_url_module

_TTL = 86400
_KEY = "images/ws_1/case/case_1/a.webp"
_UTC = dt.timezone.utc


def _now() -> dt.datetime:
    return dt.datetime.now(_UTC)


def _param(url: str, name: str) -> str:
    return re.search(rf"{name}=([^&]+)", url).group(1)


def _url_end(url: str) -> dt.datetime:
    signed_at = dt.datetime.strptime(_param(url, "X-Amz-Date"), "%Y%m%dT%H%M%SZ").replace(tzinfo=_UTC)
    return signed_at + dt.timedelta(seconds=int(_param(url, "X-Amz-Expires")))


class _RotatingRole:
    """Instance-role-like credentials: expire at a set time, refresh to a new key."""

    def __init__(self, expires_in: dt.timedelta):
        self.rotations = 0
        self.credentials = RefreshableCredentials(
            "ASIAFIRST", "secret-first", "token-first", _now() + expires_in, self._refresh, "test-role"
        )

    def _refresh(self) -> dict:
        self.rotations += 1
        return {
            "access_key": f"ASIAROTATED{self.rotations}",
            "secret_key": f"secret-{self.rotations}",
            "token": f"token-{self.rotations}",
            "expiry_time": (_now() + dt.timedelta(hours=6)).isoformat(),
        }

    def enter_refresh_window(self) -> None:
        """Nine minutes left: botocore refreshes before the next signature."""
        self.credentials._expiry_time = _now() + dt.timedelta(minutes=9)


def _client_with(monkeypatch, credentials) -> S3Client:
    monkeypatch.setattr(botocore.session.Session, "get_credentials", lambda self: credentials)
    return S3Client(bucket="test-bucket", region="eu-north-1")


@pytest.mark.unit
def test_url_is_never_stated_valid_beyond_the_signing_credentials(monkeypatch):
    role = _RotatingRole(expires_in=dt.timedelta(minutes=30))
    client = _client_with(monkeypatch, role.credentials)

    url, remaining = client.generate_presigned_get_url_with_remaining(_KEY, _TTL)

    # Before the fix: remaining was the bucket-derived ~18-24 h and X-Amz-Expires 86400,
    # while the URL died with the credentials 30 minutes later.
    assert _param(url, "X-Amz-Security-Token")
    assert _param(url, "X-Amz-Credential").startswith("ASIAFIRST")
    assert 29 * 60 <= remaining <= 30 * 60
    assert _url_end(url) <= role.credentials._expiry_time


@pytest.mark.unit
def test_rotated_credentials_are_not_served_a_cached_url_of_the_old_ones(monkeypatch):
    role = _RotatingRole(expires_in=dt.timedelta(minutes=30))
    client = _client_with(monkeypatch, role.credentials)
    first = client.generate_presigned_get_url(_KEY, _TTL)

    role.enter_refresh_window()
    second, remaining = client.generate_presigned_get_url_with_remaining(_KEY, _TTL)

    # Before the fix: the same signing bucket returned the cached URL of ASIAFIRST,
    # which expires within minutes.
    assert second != first
    assert _param(second, "X-Amz-Credential").startswith("ASIAROTATED1")
    assert _url_end(second) <= role.credentials._expiry_time
    assert remaining <= 6 * 3600


@pytest.mark.unit
def test_url_stays_byte_identical_while_the_credentials_last(monkeypatch):
    role = _RotatingRole(expires_in=dt.timedelta(hours=6))
    client = _client_with(monkeypatch, role.credentials)

    assert client.generate_presigned_get_url(_KEY, _TTL) == client.generate_presigned_get_url(_KEY, _TTL)
    assert role.rotations == 0


class _RotatesDuringSigning:
    """Credentials that rotate between the expiry read and the signature, once."""

    def __init__(self):
        self._states = [
            ("ASIAOLD", _now() + dt.timedelta(minutes=12)),
            ("ASIANEW", _now() + dt.timedelta(hours=6)),
        ]
        self._current = 0
        self.calls = 0

    @property
    def _expiry_time(self) -> dt.datetime:
        return self._states[self._current][1]

    def get_frozen_credentials(self) -> ReadOnlyCredentials:
        self.calls += 1
        if self.calls == 2:  # the signer's own read, right after the expiry read
            self._current = 1
        access_key = self._states[self._current][0]
        return ReadOnlyCredentials(access_key, f"secret-{access_key}", f"token-{access_key}")


@pytest.mark.unit
def test_a_rotation_between_expiry_read_and_signing_is_resigned(monkeypatch):
    credentials = _RotatesDuringSigning()
    client = _client_with(monkeypatch, credentials)

    url, remaining = client.generate_presigned_get_url_with_remaining(_KEY, _TTL)

    # Without the check the URL would be signed by ASIANEW but stated to end with
    # ASIAOLD, or cached under the wrong credentials.
    assert _param(url, "X-Amz-Credential").startswith("ASIANEW")
    assert remaining > 5 * 3600
    assert _url_end(url) <= credentials._expiry_time


@pytest.mark.unit
def test_static_keys_keep_the_bucket_derived_lifetime(monkeypatch):
    client = S3Client(
        bucket="test-bucket",
        region="eu-north-1",
        access_key="AKIAEXAMPLE",
        secret_key="secret",
        endpoint_url="https://s3.eu-north-1.amazonaws.com",
    )

    url, remaining = client.generate_presigned_get_url_with_remaining(_KEY, _TTL)

    assert "X-Amz-Security-Token" not in url
    assert _param(url, "X-Amz-Expires") == str(_TTL)
    assert abs(remaining - stable_presign.remaining_seconds(_KEY, _TTL)) <= 1


@pytest.mark.unit
async def test_download_url_states_the_lifetime_of_the_url_it_returns(monkeypatch):
    class _Storage:
        def generate_presigned_get_url_with_remaining(self, key, expires_in):
            return f"https://signed/{key}", 1234

    monkeypatch.setattr(get_download_url_module, "get_storage_client", lambda: _Storage())
    image = SimpleNamespace(deleted_at=None, is_public=False, image_url=_KEY)
    ctx = SimpleNamespace(
        session=SimpleNamespace(get=AsyncMock(return_value=image)),
        incoming_data={"image_client_id": "img_1"},
    )

    result = await get_download_url_module.get_download_url(ctx)

    assert result == {"download_url": f"https://signed/{_KEY}", "expires_in": 1234}
