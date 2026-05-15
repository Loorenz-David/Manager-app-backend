from beyo_manager.config import settings
from beyo_manager.services.infra.storage.base import StorageClient
from beyo_manager.services.infra.storage.local_client import LocalStorageClient
from beyo_manager.services.infra.storage.s3_client import S3Client


def get_storage_client() -> StorageClient:
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
