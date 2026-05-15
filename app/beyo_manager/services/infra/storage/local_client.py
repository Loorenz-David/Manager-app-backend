from pathlib import Path

from beyo_manager.services.infra.storage.base import StorageClient


class LocalStorageClient(StorageClient):
    def __init__(self, base_path: str, host: str = "http://localhost:5000"):
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)
        self._host = host.rstrip("/")

    def _path(self, key: str) -> Path:
        return self._base / key

    def generate_presigned_put_url(self, key: str, content_type: str, expires_in: int) -> str:
        return f"{self._host}/dev/storage/put/{key}"

    def generate_presigned_get_url(self, key: str, expires_in: int) -> str:
        return f"{self._host}/dev/storage/get/{key}"

    def head_object(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        return {"content_length": path.stat().st_size, "content_type": None}

    def delete_object(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def initiate_multipart_upload(self, key: str, content_type: str) -> str:
        return f"local-upload-{key}"

    def generate_part_presigned_url(self, key: str, upload_id: str, part_number: int, expires_in: int) -> str:
        return f"{self._host}/dev/storage/multipart/{key}/part/{part_number}"

    def complete_multipart_upload(self, key: str, upload_id: str, parts: list[dict]) -> None:
        pass  # no-op for local dev

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        pass  # no-op for local dev
