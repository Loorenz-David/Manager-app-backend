from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.issue_types.enums import IssueSourceEnum
from beyo_manager.models.tables.issue_types.issue_type import IssueType

_ISSUE_TYPES = [
    "scratches",
    "dents",
    "broken parts",
    "stains",
    "structural damage",
    "finish damage",
    "assembly issues",
    "loose joints",
    "upholstery damage",
]


async def seed_issue_types(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    issue_type_ids: dict[str, str] = {}
    for name in _ISSUE_TYPES:
        existing = await session.scalar(
            select(IssueType).where(
                IssueType.workspace_id == workspace_id,
                IssueType.name == name,
            )
        )
        if existing is not None:
            issue_type_ids[name] = existing.client_id
            continue

        issue_type = IssueType(
            workspace_id=workspace_id,
            name=name,
            source=IssueSourceEnum.INTERNAL_INSPECTION,
        )
        session.add(issue_type)
        await session.flush()
        issue_type_ids[name] = issue_type.client_id

    return issue_type_ids
