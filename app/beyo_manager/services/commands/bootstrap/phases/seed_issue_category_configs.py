from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.issue_types.issue_category_config import IssueCategoryConfig
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import WorkingSectionSupportedIssueType

_SECTION_ISSUE_TYPE_MAP: dict[str, list[str]] = {
    "structural repair": [
        "scratches",
        "dents",
        "broken parts",
        "stains",
        "structural damage",
        "finish damage",
        "loose joints",
    ],
    "sanding": [
        "scratches",
        "dents",
        "broken parts",
        "stains",
        "structural damage",
        "finish damage",
        "loose joints",
    ],
    "upholstery installation": [
        "upholstery damage",
    ],
    "assembly": [
        "assembly issues",
        "loose joints",
    ],
    "sewing": [
        "upholstery damage",
    ],
    "weaving": [
        "upholstery damage",
    ],
    "wood fix": [
        "scratches",
        "dents",
        "broken parts",
        "stains",
        "structural damage",
        "finish damage",
        "assembly issues",
        "loose joints",
    ],
}

_SEATING_CATEGORIES = [
    "armchair",
    "bench",
    "chair",
    "chairs",
    "dining chair",
    "sofa",
    "stool",
]

_WOOD_CATEGORIES = [
    "bar cabinet",
    "bedside table",
    "bookshelf",
    "cabinet",
    "chest of drawer",
    "chest of drawers",
    "coffee table",
    "conference table",
    "corner cabinet",
    "dining table",
    "hall table",
    "highboard",
    "lamp",
    "mirror",
    "nest of tables",
    "plant stand",
    "poster",
    "round table",
    "secretary",
    "serving trolley",
    "side table",
    "sideboard",
    "small table",
    "shelving",
    "sewing table",
    "trolley",
    "writing desk",
]

_WOOD_APPLICABLE_ISSUE_TYPES: frozenset[str] = frozenset(
    {
        "scratches",
        "dents",
        "broken parts",
        "stains",
        "structural damage",
        "finish damage",
        "assembly issues",
        "loose joints",
    }
)


async def seed_issue_category_configs(
    session: AsyncSession,
    workspace_id: str,
    issue_type_ids: dict[str, str],
    item_category_ids: dict[str, str],
    section_ids: dict[str, str],
) -> None:
    for section_name, issue_type_names in _SECTION_ISSUE_TYPE_MAP.items():
        section_id = section_ids[section_name]
        for issue_type_name in issue_type_names:
            issue_type_id = issue_type_ids[issue_type_name]
            existing = await session.scalar(
                select(WorkingSectionSupportedIssueType).where(
                    WorkingSectionSupportedIssueType.workspace_id == workspace_id,
                    WorkingSectionSupportedIssueType.working_section_id == section_id,
                    WorkingSectionSupportedIssueType.issue_type_id == issue_type_id,
                )
            )
            if existing is not None:
                continue

            link = WorkingSectionSupportedIssueType(
                workspace_id=workspace_id,
                working_section_id=section_id,
                issue_type_id=issue_type_id,
            )
            session.add(link)
            await session.flush()

    # Loop 1: all 9 issue types × 7 seating categories = 63 rows
    for issue_type_name, issue_type_id in issue_type_ids.items():
        for category_name in _SEATING_CATEGORIES:
            item_category_id = item_category_ids[category_name]
            existing = await session.scalar(
                select(IssueCategoryConfig).where(
                    IssueCategoryConfig.workspace_id == workspace_id,
                    IssueCategoryConfig.issue_type_id == issue_type_id,
                    IssueCategoryConfig.item_category_id == item_category_id,
                    IssueCategoryConfig.effective_from.is_(None),
                )
            )
            if existing is not None:
                continue

            config = IssueCategoryConfig(
                workspace_id=workspace_id,
                issue_type_id=issue_type_id,
                item_category_id=item_category_id,
                base_time_seconds=600,
                effective_from=None,
                effective_to=None,
            )
            session.add(config)
            await session.flush()

    # Loop 2: 8 wood-applicable issue types × 27 wood categories = 216 rows
    # "upholstery damage" is seating-only and intentionally excluded.
    for issue_type_name, issue_type_id in issue_type_ids.items():
        if issue_type_name not in _WOOD_APPLICABLE_ISSUE_TYPES:
            continue
        for category_name in _WOOD_CATEGORIES:
            item_category_id = item_category_ids[category_name]
            existing = await session.scalar(
                select(IssueCategoryConfig).where(
                    IssueCategoryConfig.workspace_id == workspace_id,
                    IssueCategoryConfig.issue_type_id == issue_type_id,
                    IssueCategoryConfig.item_category_id == item_category_id,
                    IssueCategoryConfig.effective_from.is_(None),
                )
            )
            if existing is not None:
                continue

            config = IssueCategoryConfig(
                workspace_id=workspace_id,
                issue_type_id=issue_type_id,
                item_category_id=item_category_id,
                base_time_seconds=600,
                effective_from=None,
                effective_to=None,
            )
            session.add(config)
            await session.flush()
