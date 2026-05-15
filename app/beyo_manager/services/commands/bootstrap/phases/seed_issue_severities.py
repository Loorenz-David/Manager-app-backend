from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.issue_types.issue_severity import IssueSeverity

_SEVERITIES: list[tuple[str, Decimal]] = [
    ("low", Decimal("1.1")),
    ("medium", Decimal("1.5")),
    ("high", Decimal("2.0")),
]


async def seed_issue_severities(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    severity_ids: dict[str, str] = {}
    for name, multiplier in _SEVERITIES:
        existing = await session.scalar(
            select(IssueSeverity).where(
                IssueSeverity.workspace_id == workspace_id,
                IssueSeverity.name == name,
            )
        )
        if existing is not None:
            severity_ids[name] = existing.client_id
            continue

        severity = IssueSeverity(
            workspace_id=workspace_id,
            name=name,
            time_multiplier=multiplier,
        )
        session.add(severity)
        await session.flush()
        severity_ids[name] = severity.client_id

    return severity_ids
