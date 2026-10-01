import functools
import logging
import time
from urllib.parse import quote

from beyo_manager.services.infra.storage import stable_presign
from beyo_manager.services.infra.storage.base import StorageClient

logger = logging.getLogger(__name__)

# A signature can race a credential refresh once; a second time in a row is not a race.
_SIGN_ATTEMPTS = 3


def _is_aws_endpoint(endpoint_url: str | None) -> bool:
    """True for AWS's own S3 endpoints (or none), where virtual-hosted addressing works."""
    if not endpoint_url:
        return True
    from urllib.parse import urlparse

    host = (urlparse(endpoint_url).hostname or "").lower()
    return host.endswith(".amazonaws.com")


class S3Client(StorageClient):
    def __init__(
        self,
        bucket: str,
        region: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        public_base_url: str | None = None,
    ):
        import boto3
        from botocore.config import Config

        stable_presign.register()

        self._bucket = bucket
        self._public_base_url = (
            public_base_url or f"https://{bucket}.s3.{region}.amazonaws.com"
        ).rstrip("/")
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        # Virtual-hosted addressing (<bucket>.s3.<region>.amazonaws.com): with an explicit
        # endpoint_url botocore otherwise uses path style (s3.<region>.amazonaws.com/<bucket>),
        # which needs the generic regional host. Staging's egress allow-list admits only the
        # bucket's own host (infrastructure P4a, 2026-10-01); the public item-photo URLs above
        # are already virtual-hosted. Custom endpoints (localstack, STORAGE_ENDPOINT_URL) keep
        # path style, which they need.
        s3_style = {"addressing_style": "virtual"} if _is_aws_endpoint(endpoint_url) else {}
        # Pinned explicitly: without it botocore falls back to the deprecated SigV2 in
        # us-east-1 (a no-op for regions that are SigV4-only, such as eu-north-1).
        self._client = session.client(
            "s3", endpoint_url=endpoint_url, config=Config(signature_version="s3v4", s3=s3_style)
        )
        # Separate client so quantised signing applies to GET only — backdating an
        # upload PUT URL would hand out an already-expired URL.
        self._stable_get_client = session.client(
            "s3",
            endpoint_url=endpoint_url,
            config=Config(signature_version=stable_presign.SIGNATURE_VERSION, s3=s3_style),
        )
        # The object both clients sign with. With no keys configured it is the default
        # chain's, on EC2 the instance role's: temporary, refreshed by botocore.
        self._credentials = session.get_credentials()
        self._warned_unknown_expiry: set[str] = set()
        # Signing is deterministic, so a hit and a miss return the same string — this is
        # purely a ~165us/call saving, not a correctness mechanism. bucket_start and the
        # signing access key are in the cache key, so entries for elapsed buckets and
        # for rotated credentials fall out via LRU.
        self._signed_get = functools.lru_cache(maxsize=8192)(self._sign_stable_get)

    def public_url(self, key: str) -> str:
        return f"{self._public_base_url}/{quote(key.lstrip('/'), safe='/')}"

    def _credential_window(self) -> tuple[str | None, int | None]:
        """Access key and expiry (epoch seconds) of the credentials the next signature uses.

        A URL signed with temporary credentials dies when they expire, whatever its
        X-Amz-Expires says. Static keys have no expiry: ``(access_key, None)``.
        """
        if self._credentials is None:
            return None, None
        # Refreshes first when botocore considers the credentials due for it.
        frozen = self._credentials.get_frozen_credentials()
        # botocore keeps the expiry of refreshable credentials only in this private
        # attribute (botocore is pinned; test_presign_temporary_credentials.py guards it).
        expiry = getattr(self._credentials, "_expiry_time", None)
        if expiry is not None:
            return frozen.access_key, int(expiry.timestamp())
        if frozen.token and frozen.access_key not in self._warned_unknown_expiry:
            self._warned_unknown_expiry.add(frozen.access_key)
            logger.warning(
                "S3 signing credentials are temporary but their expiry is unknown; "
                "presigned URLs may stop working before their stated expiry"
            )
        return frozen.access_key, None

    def generate_presigned_put_url(self, key: str, content_type: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def _sign_stable_get(
        self,
        key: str,
        expires_in: int,
        bucket_start: int,
        access_key: str | None,
        credentials_expire_at: int | None,
    ) -> tuple[str, int]:
        """Sign once per (key, bucket, credentials); returns the URL and its end (epoch)."""
        valid_until = bucket_start + expires_in
        if credentials_expire_at is not None:
            valid_until = min(valid_until, credentials_expire_at)
        with stable_presign.signing_key(key, bucket_start=bucket_start, access_key=access_key):
            url = self._stable_get_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                # The URL states the same end the caller is told. Deterministic: the
                # expiry is fixed per access key.
                ExpiresIn=max(1, valid_until - bucket_start),
            )
        return url, valid_until

    def generate_presigned_get_url_with_remaining(self, key: str, expires_in: int) -> tuple[str, int]:
        """Byte-stable for a given key while its signing bucket and credentials last.

        See stable_presign. Never outlives the credentials that signed it.
        """
        for _ in range(_SIGN_ATTEMPTS):
            access_key, credentials_expire_at = self._credential_window()
            try:
                url, valid_until = self._signed_get(
                    key,
                    expires_in,
                    stable_presign.bucket_start(key, expires_in),
                    access_key,
                    credentials_expire_at,
                )
            except stable_presign.CredentialsRotated:
                continue
            return url, max(0, valid_until - int(time.time()))
        raise RuntimeError("S3 signing credentials kept changing while signing")

    def generate_presigned_get_url(self, key: str, expires_in: int) -> str:
        return self.generate_presigned_get_url_with_remaining(key, expires_in)[0]

    def head_object(self, key: str) -> dict | None:
        from botocore.exceptions import ClientError

        try:
            resp = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return None
            raise
        return {
            "content_length": resp["ContentLength"],
            "content_type": resp.get("ContentType"),
            "last_modified": resp.get("LastModified"),
        }

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def initiate_multipart_upload(self, key: str, content_type: str) -> str:
        resp = self._client.create_multipart_upload(
            Bucket=self._bucket, Key=key, ContentType=content_type
        )
        return resp["UploadId"]

    def generate_part_presigned_url(self, key: str, upload_id: str, part_number: int, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=expires_in,
        )

    def complete_multipart_upload(self, key: str, upload_id: str, parts: list[dict]) -> None:
        self._client.complete_multipart_upload(
            Bucket=self._bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        self._client.abort_multipart_upload(
            Bucket=self._bucket, Key=key, UploadId=upload_id
        )
