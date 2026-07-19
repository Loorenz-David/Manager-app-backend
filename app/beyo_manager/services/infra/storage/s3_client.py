import functools

from beyo_manager.services.infra.storage import stable_presign
from beyo_manager.services.infra.storage.base import StorageClient


class S3Client(StorageClient):
    def __init__(
        self,
        bucket: str,
        region: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
    ):
        import boto3
        from botocore.config import Config

        stable_presign.register()

        self._bucket = bucket
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        # Pinned explicitly: without it botocore falls back to the deprecated SigV2 in
        # us-east-1 (a no-op for regions that are SigV4-only, such as eu-north-1).
        self._client = session.client(
            "s3", endpoint_url=endpoint_url, config=Config(signature_version="s3v4")
        )
        # Separate client so quantised signing applies to GET only — backdating an
        # upload PUT URL would hand out an already-expired URL.
        self._stable_get_client = session.client(
            "s3",
            endpoint_url=endpoint_url,
            config=Config(signature_version=stable_presign.SIGNATURE_VERSION),
        )
        # Signing is deterministic, so a hit and a miss return the same string — this is
        # purely a ~165us/call saving, not a correctness mechanism. bucket_start is in
        # the cache key, so entries for elapsed buckets fall out via LRU.
        self._signed_get = functools.lru_cache(maxsize=8192)(self._sign_stable_get)

    def generate_presigned_put_url(self, key: str, content_type: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def _sign_stable_get(self, key: str, expires_in: int, bucket_start: int) -> str:
        # bucket_start is unused in the body — it is the cache key that makes each
        # signing bucket a distinct entry.
        with stable_presign.signing_key(key):
            return self._stable_get_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    def generate_presigned_get_url(self, key: str, expires_in: int) -> str:
        """Byte-stable for a given key within its signing bucket. See stable_presign."""
        return self._signed_get(
            key, expires_in, stable_presign.bucket_start(key, expires_in)
        )

    def presigned_get_remaining_seconds(self, key: str, expires_in: int) -> int:
        return stable_presign.remaining_seconds(key, expires_in)

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
