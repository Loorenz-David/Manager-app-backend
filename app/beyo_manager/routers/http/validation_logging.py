"""Log FastAPI request-validation refusals (422) by field, then answer exactly as before.

Without this, a request whose body or query failed the route's schema left one access-log
line — `"PUT /api/v1/tasks" 422` — and nothing saying which field. That cost a production
trace on 2026-11-16 (a pre-order missing `shopify_preorder.product.price`), which could only
be inferred from the response size.

What is logged: the method, the path WITHOUT its query string, and per failing field its
location (`body.shopify_preorder.product.price`) and pydantic error type (`missing`,
`int_parsing`, ...). What is never logged: the submitted values, pydantic's `input`, its
`msg` (a custom validator's message may quote the value), and the query string (lookups put
customer emails in it). Request bodies here carry customer names, emails and phone numbers.

The response is FastAPI's own handler, so clients see the same 422 body as before.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Enough to see what is wrong; a malformed body can fail on hundreds of fields.
MAX_LOGGED_FIELDS = 20


def _field_location(loc: object) -> str:
    if not isinstance(loc, (list, tuple)):
        return str(loc)
    return ".".join(str(part) for part in loc)


def describe_validation_failures(exc: RequestValidationError) -> list[dict[str, str]]:
    """Location and error type per failing field: no values, inputs or messages."""
    return [
        {"loc": _field_location(error.get("loc", ())), "type": str(error.get("type", "unknown"))}
        for error in exc.errors()[:MAX_LOGGED_FIELDS]
    ]


async def log_request_validation_error(request: Request, exc: Exception) -> JSONResponse:
    # Registered only for RequestValidationError; typed `Exception` because that is the
    # handler signature Starlette declares.
    if not isinstance(exc, RequestValidationError):
        raise exc
    fields = describe_validation_failures(exc)
    error_count = len(exc.errors())
    logger.info(
        "Request validation failed %s %s | fields=%s%s",
        request.method,
        request.url.path,
        "; ".join(f"{field['loc']} ({field['type']})" for field in fields),
        f" (+{error_count - len(fields)} more)" if error_count > len(fields) else "",
        extra={
            "event_type": "request.validation_error",
            "method": request.method,
            "path": request.url.path,
            "status_code": 422,
            "error_count": error_count,
            "fields": fields,
        },
    )
    return await request_validation_exception_handler(request, exc)
