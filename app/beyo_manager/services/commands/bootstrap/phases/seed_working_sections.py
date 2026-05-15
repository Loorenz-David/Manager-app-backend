from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency

_SECTIONS = [
    "disassembly",
    "cleaning",
    "structural repair",
    "sanding",
    "upholstery removal",
    "padding",
    "upholstery installation",
    "assembly",
    "sewing",
    "weaving",
    "wood fix",
    "ground oil",
    "hardwax oil",
]

_DEPENDENCIES: list[tuple[str, str]] = [
    ("cleaning", "disassembly"),
    ("structural repair", "disassembly"),
    ("sanding", "structural repair"),
    ("upholstery removal", "disassembly"),
    ("padding", "upholstery removal"),
    ("upholstery installation", "padding"),
    ("upholstery installation", "upholstery removal"),
    ("assembly", "upholstery installation"),
    ("assembly", "structural repair"),
    ("assembly", "sanding"),
    ("sewing", "disassembly"),
    ("sewing", "upholstery removal"),
    ("weaving", "sewing"),
    ("ground oil", "wood fix"),
    ("hardwax oil", "wood fix"),
]


async def seed_working_sections(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    section_ids: dict[str, str] = {}
    for name in _SECTIONS:
        existing = await session.scalar(
            select(WorkingSection).where(
                WorkingSection.workspace_id == workspace_id,
                WorkingSection.name == name,
            )
        )
        if existing is not None:
            section_ids[name] = existing.client_id
            continue

        section = WorkingSection(workspace_id=workspace_id, name=name, image=None)
        session.add(section)
        await session.flush()
        section_ids[name] = section.client_id

    for dependent_name, prerequisite_name in _DEPENDENCIES:
        dependent_section_id = section_ids[dependent_name]
        prerequisite_section_id = section_ids[prerequisite_name]
        existing = await session.scalar(
            select(WorkingSectionDependency).where(
                WorkingSectionDependency.workspace_id == workspace_id,
                WorkingSectionDependency.dependent_section_id == dependent_section_id,
                WorkingSectionDependency.prerequisite_section_id == prerequisite_section_id,
            )
        )
        if existing is not None:
            continue

        dependency = WorkingSectionDependency(
            workspace_id=workspace_id,
            dependent_section_id=dependent_section_id,
            prerequisite_section_id=prerequisite_section_id,
        )
        session.add(dependency)
        await session.flush()

    return section_ids
