"""Deterministic (byte-stable) presigned S3 GET URLs.

boto3 stamps ``X-Amz-Date`` with the wall clock at signing time, so presigning the
same object twice a second apart yields two different signatures. Every API response
therefore carried a fresh ``image_url`` for an unchanged image, which defeated browser
HTTP caching and forced clients to re-download every visible image on every refetch.

The fix is to *quantise the signing clock*: floor ``X-Amz-Date`` to a bucket boundary
before signing. The signature then becomes a pure function of
``(key, bucket_start, credentials)`` — identical across every worker, every instance and
across restarts, with no shared cache to maintain.

Backdating is safe: SigV4 validity is ``X-Amz-Date + X-Amz-Expires``, so a backdated URL
is simply shorter-lived. Bucket width is capped at a quarter of the TTL, which guarantees
a returned URL always has at least 75% of its TTL left.

Scoping matters: this must apply to GET URLs only. Backdating a 15-minute upload PUT URL
by hours would hand out already-expired URLs, so this signer is registered under a private
signature version and used by a dedicated client — see ``S3Client``.

Temporary credentials (an EC2 instance role) end a URL's validity when they expire,
whatever ``X-Amz-Expires`` says. ``S3Client`` therefore caps each URL at the expiry of the
credentials that sign it, and this signer refuses to sign with credentials other than the
ones that cap was computed for (:class:`CredentialsRotated`).
"""

import contextlib
import contextvars
import dataclasses
import datetime
import hashlib
import time

import botocore.auth
from botocore.exceptions import NoCredentialsError


class CredentialsRotated(Exception):
    """The credentials changed between reading their expiry and signing with them."""


@dataclasses.dataclass(frozen=True)
class _SigningContext:
    key: str
    bucket_start: int | None
    access_key: str | None


# The signer needs the storage key to derive this key's bucket offset, and botocore
# offers no way to thread custom context into generate_presigned_url. Presigning is
# fully synchronous with no await between set and read, so a ContextVar is exact.
_signing_context: contextvars.ContextVar[_SigningContext | None] = contextvars.ContextVar(
    "beyo_stable_signing_context", default=None
)


@contextlib.contextmanager
def signing_key(key: str, *, bucket_start: int | None = None, access_key: str | None = None):
    """Scope one signature.

    ``bucket_start`` pins X-Amz-Date (otherwise derived from the key and X-Amz-Expires);
    ``access_key``, when given, is the only credential allowed to sign.
    """
    token = _signing_context.set(_SigningContext(key, bucket_start, access_key))
    try:
        yield
    finally:
        _signing_context.reset(token)

# Private signature version. `RequestSigner._choose_signer` appends "-query" for
# presign-url signing, so a client configured with SIGNATURE_VERSION resolves to
# SIGNATURE_VERSION + "-query" in AUTH_TYPE_MAPS.
SIGNATURE_VERSION = "beyo-stable-s3v4"
_AUTH_TYPE = f"{SIGNATURE_VERSION}-query"

# Upper bound on bucket width. Wider buckets mean fewer distinct URLs (better cache hit
# rates) but more TTL sacrificed to backdating.
MAX_BUCKET_SECONDS = 6 * 3600
MIN_BUCKET_SECONDS = 60


def bucket_seconds(expires_in: int) -> int:
    """Bucket width for a given TTL, capped so a URL keeps >=75% of its TTL."""
    return max(MIN_BUCKET_SECONDS, min(MAX_BUCKET_SECONDS, expires_in // 4))


def _key_offset(key: str, width: int) -> int:
    """Deterministic per-key offset within the bucket window.

    Without this every URL in the system would rotate on the same boundary, so every
    client would re-download every image simultaneously. Offsetting by a hash of the key
    spreads rotations evenly across the window.

    Uses blake2b rather than hash() — the builtin is salted per process and would give
    each worker a different offset for the same key.
    """
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % width


def bucket_start(key: str, expires_in: int, now: float | None = None) -> int:
    """Epoch seconds of the current signing bucket for this key."""
    current = int(time.time() if now is None else now)
    width = bucket_seconds(expires_in)
    offset = _key_offset(key, width)
    return ((current - offset) // width) * width + offset


def remaining_seconds(key: str, expires_in: int, now: float | None = None) -> int:
    """Actual remaining validity of the URL this key currently signs to.

    Always in (expires_in - bucket_width, expires_in].
    """
    current = int(time.time() if now is None else now)
    return bucket_start(key, expires_in, now=current) + expires_in - current


class StableS3SigV4QueryAuth(botocore.auth.S3SigV4QueryAuth):
    """S3 SigV4 query signer that stamps a quantised X-Amz-Date.

    Mirrors ``SigV4Auth.add_auth`` (botocore is pinned in requirements.txt) with the sole
    change that the timestamp is floored to a bucket boundary instead of read from the
    wall clock. ``test_stable_presign.py`` fails loudly if a botocore upgrade breaks this.
    """

    def add_auth(self, request):
        if self.credentials is None:
            raise NoCredentialsError()
        context = _signing_context.get()
        if context is not None and context.access_key is not None:
            if self.credentials.access_key != context.access_key:
                raise CredentialsRotated()
        # Falls back to the URL (which embeds the key) if no key was scoped in, so the
        # signer still produces stable output rather than silently reverting to now().
        if context is not None and context.bucket_start is not None:
            start = context.bucket_start
        else:
            key = context.key if context is not None else request.url
            start = bucket_start(key, int(self._expires))
        request.context["timestamp"] = datetime.datetime.fromtimestamp(
            start, datetime.UTC
        ).strftime(botocore.auth.SIGV4_TIMESTAMP)
        self._modify_request_before_signing(request)
        canonical_request = self.canonical_request(request)
        string_to_sign = self.string_to_sign(request, canonical_request)
        self._inject_signature_to_request(
            request, self.signature(string_to_sign, request)
        )


def register() -> None:
    """Make the stable signer resolvable by botocore. Idempotent."""
    botocore.auth.AUTH_TYPE_MAPS[_AUTH_TYPE] = StableS3SigV4QueryAuth
