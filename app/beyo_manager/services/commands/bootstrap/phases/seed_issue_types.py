from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.issue_types.enums import IssueModeEnum, IssueSourceEnum
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.services.commands.bootstrap.phases.seed_item_categories import _SEATING_CATEGORIES


def _seat_map_for_placements(*placements: str) -> dict[str, list[str]]:
    return {category_name: list(placements) for category_name in _SEATING_CATEGORIES}


ISSUE_DEFINITIONS: list[dict] = [
    {
        "name": "Upholstery Damage",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["disassembly"],
        "item_category_placements": _seat_map_for_placements("seat part"),
    },
    {
        "name": "Padding Damage",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["disassembly"],
        "item_category_placements": _seat_map_for_placements("seat part"),
    },
    {
        "name": "Screws",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["disassembly", "structural repair"],
        "item_category_placements": _seat_map_for_placements("missing", "frame"),
    },
    {
        "name": "Seat",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["disassembly"],
        "item_category_placements": _seat_map_for_placements("missing"),
    },
    {
        "name": "Backrest",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["disassembly"],
        "item_category_placements": _seat_map_for_placements("missing"),
    },
    {
        "name": "Scratches",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.GRADED,
        "working_sections": ["cleaning wood", "structural repair", "sanding"],
        "item_category_placements": _seat_map_for_placements("frame"),
    },
    {
        "name": "Veneer Damage",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.GRADED,
        "working_sections": ["cleaning wood", "structural repair", "sanding"],
        "item_category_placements": _seat_map_for_placements("frame"),
    },
    {
        "name": "Cracks",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.GRADED,
        "working_sections": ["cleaning wood", "structural repair", "sanding"],
        "item_category_placements": _seat_map_for_placements("frame"),
    },
    {
        "name": "Chips",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.GRADED,
        "working_sections": ["cleaning wood", "structural repair", "sanding"],
        "item_category_placements": _seat_map_for_placements("frame"),
    },
    {
        "name": "Water Damage",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["cleaning wood", "structural repair", "sanding", "upholstery removal"],
        "item_category_placements": _seat_map_for_placements("frame", "seat part"),
    },
    {
        "name": "Woodworms",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["cleaning wood", "structural repair", "sanding", "upholstery removal"],
        "item_category_placements": _seat_map_for_placements("frame", "seat part"),
    },
    {
        "name": "Wooden Part",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["structural repair"],
        "item_category_placements": _seat_map_for_placements("missing"),
    },
    {
        "name": "Unstable",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["structural repair"],
        "item_category_placements": _seat_map_for_placements("frame"),
    },
    {
        "name": "Springs / Ribbon Damage",
        "source": IssueSourceEnum.INTERNAL_INSPECTION,
        "issue_mode": IssueModeEnum.SWITCH,
        "working_sections": ["upholstery removal"],
        "item_category_placements": _seat_map_for_placements("seat part"),
    },
]


def _validate_issue_definitions() -> None:
    seating_categories = set(_SEATING_CATEGORIES)
    known_issue_names: set[str] = set()
    for issue_definition in ISSUE_DEFINITIONS:
        issue_name = issue_definition["name"]
        if issue_name in known_issue_names:
            raise ValueError(f"Duplicate issue definition name: {issue_name!r}")
        known_issue_names.add(issue_name)

        item_category_placements: dict[str, list[str]] = issue_definition["item_category_placements"]
        if set(item_category_placements.keys()) != seating_categories:
            raise ValueError(
                f"Issue definition {issue_name!r} must include all Seat categories explicitly."
            )
        for category_name, placements in item_category_placements.items():
            if category_name not in seating_categories:
                raise ValueError(f"Unknown Seat category in issue map: {category_name!r}")
            if not placements:
                raise ValueError(
                    f"Issue definition {issue_name!r} must declare at least one placement for {category_name!r}."
                )


_validate_issue_definitions()


async def seed_issue_types(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    issue_type_ids: dict[str, str] = {}
    for issue_definition in ISSUE_DEFINITIONS:
        name = issue_definition["name"]
        source = issue_definition["source"]
        issue_mode = issue_definition["issue_mode"]

        existing = await session.scalar(
            select(IssueType).where(
                IssueType.workspace_id == workspace_id,
                IssueType.name == name,
            )
        )
        if existing is not None:
            existing.source = source
            existing.issue_mode = issue_mode
            await session.flush()
            issue_type_ids[name] = existing.client_id
            continue

        issue_type = IssueType(
            workspace_id=workspace_id,
            name=name,
            source=source,
            issue_mode=issue_mode,
        )
        session.add(issue_type)
        await session.flush()
        issue_type_ids[name] = issue_type.client_id

    return issue_type_ids
