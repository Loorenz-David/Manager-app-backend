from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.models.tables.cases.case_type import CaseType

_CASE_TYPES: list[dict[str, str]] = [
    {
        "name": "Missing Item",
        "legacy_name": "missing_item",
        "description": "The required item is not available at the workstation.",
        "image_url": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/missing_item.webp",
    },
    {
        "name": "Missing Materials",
        "legacy_name": "missing_materials",
        "description": "Required materials are not available to continue the task.",
        "image_url": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/missing_materials.webp",
    },
    {
        "name": "No Fabric",
        "legacy_name": "no_fabric",
        "description": "No suitable fabric is available for this task.",
        "image_url": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/no_fabric.webp",
    },
    {
        "name": "Unclear Task",
        "legacy_name": "unclear_task",
        "description": "Task instructions are unclear and need clarification.",
        "image_url": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/unclear_task.webp",
    },
    {
        "name": "Broken Tool",
        "legacy_name": "broken_tool",
        "description": "A required tool is broken and cannot be used safely.",
        "image_url": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/broken_tool.webp",
    },
    {
        "name": "Wrong Fabric",
        "legacy_name": "wrong_fabric",
        "description": "The available fabric does not match task requirements.",
        "image_url": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/wrong_fabric.webp",
    },
]


async def seed_case_types(session: AsyncSession) -> dict[str, str]:
    case_type_ids: dict[str, str] = {}

    for entry in _CASE_TYPES:
        existing = await session.scalar(
            select(CaseType).where(
                CaseType.name == entry["name"],
                CaseType.entity_type == CaseLinkEntityTypeEnum.TASK,
            )
        )

        if existing is None:
            existing = await session.scalar(
                select(CaseType).where(
                    CaseType.name == entry["legacy_name"],
                    CaseType.entity_type == CaseLinkEntityTypeEnum.TASK,
                )
            )

        if existing is not None:
            if existing.name != entry["name"]:
                existing.name = entry["name"]
            if existing.description != entry["description"]:
                existing.description = entry["description"]
            if existing.image_url != entry["image_url"]:
                existing.image_url = entry["image_url"]
            case_type_ids[entry["name"]] = existing.client_id
            continue

        case_type = CaseType(
            name=entry["name"],
            image_url=entry["image_url"],
            description=entry["description"],
            entity_type=CaseLinkEntityTypeEnum.TASK,
        )
        session.add(case_type)
        await session.flush()
        case_type_ids[entry["name"]] = case_type.client_id

    return case_type_ids