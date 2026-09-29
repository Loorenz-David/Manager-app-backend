from abc import ABC, abstractmethod


class StorageClient(ABC):
    @abstractmethod
    def public_url(self, key: str) -> str:
        """Return the stable public URL for an object key."""

    @abstractmethod
    def generate_presigned_put_url(self, key: str, content_type: str, expires_in: int) -> str: ...

    @abstractmethod
    def generate_presigned_get_url(self, key: str, expires_in: int) -> str: ...

    def generate_presigned_get_url_with_remaining(self, key: str, expires_in: int) -> tuple[str, int]:
        """The URL `generate_presigned_get_url` returns now, with its actual remaining validity.

        One call, so the two always describe the same signature. S3 returns less than the
        full TTL: its URLs are backdated, and end with the credentials that signed them.
        Backends whose URLs do not expire return the TTL.
        """
        return self.generate_presigned_get_url(key, expires_in), expires_in

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
