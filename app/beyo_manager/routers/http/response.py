from fastapi import HTTPException
from fastapi.responses import JSONResponse

from beyo_manager.errors.availability import AuthUnavailableError
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
    if isinstance(error, AuthUnavailableError):
        return JSONResponse(
            content=_auth_unavailable_body(error),
            status_code=error.http_status,
            headers=_auth_unavailable_headers(error),
        )
    return JSONResponse(
        content={"error": error.message, "ok": False},
        status_code=error.http_status,
    )


def auth_unavailable_http_exception(error: AuthUnavailableError | None = None) -> HTTPException:
    """The same 503 for a FastAPI dependency (which can only raise, not return).

    With no exception handlers registered, FastAPI renders it as
    ``{"detail": {"error", "ok": false, "code": "auth_unavailable", ...}}`` plus the
    ``Retry-After`` header — the client detects ``detail.code``.
    """
    error = error or AuthUnavailableError()
    return HTTPException(
        status_code=error.http_status,
        detail=_auth_unavailable_body(error),
        headers=_auth_unavailable_headers(error),
    )


def _auth_unavailable_body(error: AuthUnavailableError) -> dict:
    body: dict = {"error": error.message, "ok": False, "code": error.code}
    if error.reason:
        body["reason"] = error.reason
    return body


def _auth_unavailable_headers(error: AuthUnavailableError) -> dict[str, str]:
    return {"Retry-After": str(error.retry_after_seconds)}
