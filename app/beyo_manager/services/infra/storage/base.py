from abc import ABC, abstractmethod


class StorageClient(ABC):
    @abstractmethod
    def generate_presigned_put_url(self, key: str, content_type: str, expires_in: int) -> str: ...

    @abstractmethod
    def generate_presigned_get_url(self, key: str, expires_in: int) -> str: ...

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
