from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.audit.audit_log import AuditLog

if TYPE_CHECKING:
    from fastapi import Request


async def write_audit(
    session: AsyncSession,
    event: str,
    workspace_id: str,
    actor_user_id: str | None = None,
    actor_label:   str | None = None,
    resource_type: str | None = None,
    resource_client_id: str | None = None,
    detail: dict | None = None,
    request: "Request | None" = None,
) -> None:
    """Write one audit log entry inside the caller's open transaction."""
    ip_address  = _get_ip(request) if request else None
    user_agent  = request.headers.get("User-Agent", "")[:512] if request else None
    request_id  = getattr(getattr(request, "state", None), "request_id", None) if request else None

    entry = AuditLog(
        event=event,
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_client_id=resource_client_id,
        detail=detail or {},
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)


async def write_audit_from_event(
    session: AsyncSession,
    event_name: str,
    workspace_id: str,
    resource_client_id: str | None = None,
    detail: dict | None = None,
    occurred_at: datetime | None = None,
) -> None:
    """Lightweight audit write for event-bus audit_handler (no Request available)."""
    entry = AuditLog(
        event=event_name,
        workspace_id=workspace_id,
        resource_client_id=resource_client_id,
        detail=detail or {},
        created_at=occurred_at or datetime.now(timezone.utc),
    )
    session.add(entry)


def _get_ip(request: "Request") -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
