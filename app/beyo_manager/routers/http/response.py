from fastapi.responses import JSONResponse

from beyo_manager.errors.base import DomainError


def build_ok(data: dict | list | None = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content={"data": data, "ok": True}, status_code=status_code)


def build_err(error: DomainError) -> JSONResponse:
    return JSONResponse(
        content={"error": error.message, "ok": False},
        status_code=error.http_status,
    )
