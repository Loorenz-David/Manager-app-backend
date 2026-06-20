from fastapi.responses import JSONResponse

from beyo_manager.errors.base import DomainError


def build_ok(
    data: dict | list | None = None,
    status_code: int = 200,
    warnings: list[str] | None = None,
) -> JSONResponse:
    return JSONResponse(content={"data": data, "ok": True, "warnings": warnings or []}, status_code=status_code)


def build_err(error: DomainError | str) -> JSONResponse:
    if isinstance(error, str):
        return JSONResponse(
            content={"error": error, "ok": False},
            status_code=400,
        )
    return JSONResponse(
        content={"error": error.message, "ok": False},
        status_code=error.http_status,
    )
