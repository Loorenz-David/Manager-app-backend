from abc import ABC, abstractmethod


class StorageClient(ABC):
    @abstractmethod
    def generate_presigned_put_url(self, key: str, content_type: str, expires_in: int) -> str: ...

    @abstractmethod
    def generate_presigned_get_url(self, key: str, expires_in: int) -> str: ...

    def presigned_get_remaining_seconds(self, key: str, expires_in: int) -> int:
        """Actual remaining validity of the URL `generate_presigned_get_url` returns now.

        Backends that stabilise URLs by backdating the signature (S3) return less than the
        full TTL and override this. Backends whose URLs do not expire return the TTL.
        """
        return expires_in

    @abstractmethod
    def head_object(self, key: str) -> dict | None:
        """Return object metadata or None when the object does not exist."""

    @abstractmethod
    def delete_object(self, key: str) -> None: ...

    @abstractmethod
    def initiate_multipart_upload(self, key: str, content_type: str) -> str:
        """Returns upload_id."""

    @abstractmethod
    def generate_part_presigned_url(self, key: str, upload_id: str, part_number: int, expires_in: int) -> str:
        """Returns presigned PUT URL for one part. part_number is 1-indexed."""

    @abstractmethod
    def complete_multipart_upload(self, key: str, upload_id: str, parts: list[dict]) -> None:
        """parts: [{"PartNumber": 1, "ETag": "..."}]"""

    @abstractmethod
    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        """Called on timeout or orphan cleanup."""
