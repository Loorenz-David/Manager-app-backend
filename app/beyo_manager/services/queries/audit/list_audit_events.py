from datetime import datetime

from sqlalchemy import select

from beyo_manager.models.tables.audit.audit_log import AuditLog
from beyo_manager.services.context import ServiceContext


async def list_audit_events(ctx: ServiceContext) -> dict:
    """List audit events scoped to the caller's workspace.
    Query params (all optional):
      event, actor_user_id, resource_client_id, since (ISO), until (ISO), limit (int).
    """
    params = ctx.incoming_data
    limit  = min(int(params.get("limit", 50)), 200)

    stmt = select(AuditLog).where(AuditLog.workspace_id == ctx.workspace_id)

    if params.get("event"):
        stmt = stmt.where(AuditLog.event == params["event"])
    if params.get("actor_user_id"):
        stmt = stmt.where(AuditLog.actor_user_id == params["actor_user_id"])
    if params.get("resource_client_id"):
        stmt = stmt.where(AuditLog.resource_client_id == params["resource_client_id"])
    if params.get("since"):
        stmt = stmt.where(AuditLog.created_at >= datetime.fromisoformat(params["since"]))
    if params.get("until"):
        stmt = stmt.where(AuditLog.created_at <= datetime.fromisoformat(params["until"]))

    stmt   = stmt.order_by(AuditLog.created_at.desc()).limit(limit + 1)
    result = await ctx.session.execute(stmt)
    rows   = result.scalars().all()

    has_more = len(rows) > limit
    return {
        "events":   [_serialize(e) for e in rows[:limit]],
        "has_more": has_more,
    }


def _serialize(entry: AuditLog) -> dict:
    return {
        "client_id":         entry.client_id,
        "event":             entry.event,
        "actor":             entry.actor_label or f"user:{entry.actor_user_id}",
        "resource_type":     entry.resource_type,
        "resource_id":       entry.resource_client_id,
        "detail":            entry.detail,
        "ip_address":        entry.ip_address,
        "occurred_at":       entry.created_at.isoformat(),
    }
