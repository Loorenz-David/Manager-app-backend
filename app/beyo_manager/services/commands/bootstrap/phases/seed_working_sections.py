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

_SECTION_IMAGE_URLS: dict[str, str] = {
    "assembly": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/assembly.webp",
    "cleaning": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/cleaning_2.webp",
    "disassembly": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/dismantler.webp",
    "structural repair": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/gluing_2.webp",
    "ground oil": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/ground_oil.webp",
    "hardwax oil": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/hardwax.webp",
    "padding": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/padding.webp",
    "sanding": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/sander.webp",
    "sewing": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/sewing.webp",
    "upholstery installation": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/upholstery_installer.webp",
    "upholstery removal": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/upholstery_remover_2.webp",
    "wood fix": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/wood_oil.webp",
}

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

        section = WorkingSection(workspace_id=workspace_id, name=name, image=_SECTION_IMAGE_URLS.get(name))
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
