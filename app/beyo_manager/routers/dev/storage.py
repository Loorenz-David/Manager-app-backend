"""Dev-only local file storage endpoints.

Registered only when settings.environment == 'development'.  Simulates the
presigned PUT/GET URL flow without real object storage.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from beyo_manager.config import settings

router = APIRouter()


def _resolve(key: str) -> Path:
    base = Path(settings.local_storage_path)
    path = (base / key).resolve()
    if not str(path).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid key")
    return path


@router.put("/dev/storage/put/{key:path}")
async def dev_storage_put(key: str, request: Request) -> Response:
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = await request.body()
    path.write_bytes(body)
    return Response(status_code=200)


@router.get("/dev/storage/get/{key:path}")
async def dev_storage_get(key: str) -> FileResponse:
    path = _resolve(key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Object not found")
    return FileResponse(str(path))
