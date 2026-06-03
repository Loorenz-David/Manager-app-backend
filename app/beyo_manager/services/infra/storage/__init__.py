from beyo_manager.config import settings
from beyo_manager.services.infra.storage.base import StorageClient
from beyo_manager.services.infra.storage.local_client import LocalStorageClient
from beyo_manager.services.infra.storage.s3_client import S3Client


_cached_storage_client: StorageClient | None = None
_cached_storage_signature: tuple[str | None, ...] | None = None


def _current_storage_signature() -> tuple[str | None, ...]:
    return (
        settings.storage_provider,
        settings.storage_bucket,
        settings.storage_region,
        settings.storage_endpoint_url,
        settings.aws_access_key_id,
        settings.aws_secret_access_key,
        settings.local_storage_path,
        settings.local_storage_host,
    )


def _build_storage_client() -> StorageClient:
    provider = settings.storage_provider
    if provider == "s3":
        if not settings.storage_bucket:
            raise RuntimeError("STORAGE_BUCKET must be set when STORAGE_PROVIDER=s3")
        region = settings.storage_region or "us-east-1"
        return S3Client(
            bucket=settings.storage_bucket,
            region=region,
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key,
            endpoint_url=settings.storage_endpoint_url or f"https://s3.{region}.amazonaws.com",
        )
    if provider == "localstack":
        if not settings.storage_bucket:
            raise RuntimeError("STORAGE_BUCKET must be set when STORAGE_PROVIDER=localstack")
        return S3Client(
            bucket=settings.storage_bucket,
            region=settings.storage_region or "us-east-1",
            endpoint_url=settings.storage_endpoint_url or "http://localhost:4566",
        )
    return LocalStorageClient(base_path=settings.local_storage_path, host=settings.local_storage_host)


def get_storage_client() -> StorageClient:
    global _cached_storage_client, _cached_storage_signature

    signature = _current_storage_signature()
    if _cached_storage_client is None or _cached_storage_signature != signature:
        _cached_storage_client = _build_storage_client()
        _cached_storage_signature = signature

    return _cached_storage_client
