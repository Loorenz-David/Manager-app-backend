from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency

# Toggle creation per working section.
# Set any section to False to skip creating it during bootstrap.
_SECTION_CREATION_MAP: dict[str, bool] = {
    "disassembly": True,
    "cleaning seat": True,
    "cleaning wood": True,
    "structural repair": True,
    "sanding": True,
    "upholstery removal": True,
    "padding": True,
    "upholstery installation": True,
    "assembly": True,
    "sewing": True,
    "weaving": True,
    "wood fix": True,
    "ground oil": True,
    "hardwax oil": True,
    "photography": True,
}

_SECTION_IMAGE_URLS: dict[str, str] = {
    "assembly": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/assembly.webp",
    "cleaning seat": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/cleaning_2.webp",
    "cleaning wood": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/cleaning_2.webp",
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
    "photography": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/working_sections/photography.webp",
}

_SECTION_ORDER_LISTS: dict[str, int] = {
    "disassembly": 1,
    "cleaning seat": 2,
    "cleaning wood": 2,
    "structural repair": 3,
    "sanding": 4,
    "upholstery removal": 5,
    "padding": 6,
    "upholstery installation": 7,
    "assembly": 8,
    "sewing": 9,
    "weaving": 7,
    "wood fix": 1,
    "ground oil": 2,
    "hardwax oil": 3,
    "photography": 10,
}

_SECTION_BATCH_MAP: dict[str, bool] = {
    "ground oil": True,
    "hardwax oil": True,
    "photography": True,
}

_DEPENDENCIES: list[tuple[str, str]] = [
    ("cleaning seat", "disassembly"),
    ("cleaning wood", "disassembly"),
    ("structural repair", "disassembly"),
    ("structural repair", "cleaning wood"),
    ("sanding", "structural repair"),
    ("sanding", "cleaning wood"),
    ("sanding", "disassembly"),
    ("upholstery removal", "disassembly"),
    ("padding", "upholstery removal"),
    ("padding", "disassembly"),
    ("upholstery installation", "padding"),
    ("upholstery installation", "upholstery removal"),
    ("upholstery installation", "disassembly"),
    ("assembly", "disassembly"),
    ("assembly", "cleaning seat"),
    ("assembly", "cleaning wood"),
    ("assembly", "structural repair"),
    ("assembly", "sanding"),
    ("assembly", "upholstery removal"),
    ("assembly", "padding"),
    ("assembly", "upholstery installation"),
    ("sewing", "padding"),
    ("sewing", "upholstery removal"),
    ("sewing", "disassembly"),
    ("weaving", "padding"),
    ("weaving", "upholstery removal"),
    ("weaving", "disassembly"),
    ("ground oil", "wood fix"),
    ("hardwax oil", "wood fix"),
    ("hardwax oil", "ground oil"),
    ("photography", "disassembly"),
    ("photography", "cleaning seat"),
    ("photography", "cleaning wood"),
    ("photography", "structural repair"),
    ("photography", "sanding"),
    ("photography", "upholstery removal"),
    ("photography", "padding"),
    ("photography", "upholstery installation"),
    ("photography", "assembly"),
    ("photography", "sewing"),
    ("photography", "weaving"),
    ("photography", "wood fix"),
    ("photography", "ground oil"),
    ("photography", "hardwax oil"),
]


async def seed_working_sections(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    section_ids: dict[str, str] = {}
    for name, should_create in _SECTION_CREATION_MAP.items():
        if not should_create:
            continue

        existing = await session.scalar(
            select(WorkingSection).where(
                WorkingSection.workspace_id == workspace_id,
                WorkingSection.name == name,
            )
        )
        if existing is not None:
            existing.image = _SECTION_IMAGE_URLS.get(name)
            existing.order_list = _SECTION_ORDER_LISTS.get(name)
            existing.allows_batch_working = _SECTION_BATCH_MAP.get(name, False)
            await session.flush()
            section_ids[name] = existing.client_id
            continue

        section = WorkingSection(
            workspace_id=workspace_id,
            name=name,
            image=_SECTION_IMAGE_URLS.get(name),
            order_list=_SECTION_ORDER_LISTS.get(name),
            allows_batch_working=_SECTION_BATCH_MAP.get(name, False),
        )
        session.add(section)
        await session.flush()
        section_ids[name] = section.client_id

    for dependent_name, prerequisite_name in _DEPENDENCIES:
        if dependent_name not in section_ids or prerequisite_name not in section_ids:
            continue

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
