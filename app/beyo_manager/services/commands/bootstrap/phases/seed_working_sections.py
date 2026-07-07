from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency
from beyo_manager.models.tables.working_sections.working_section_item_category import WorkingSectionItemCategory
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)

# Toggle creation per working section.
# Set any section to False to skip creating it during bootstrap.
_SECTION_CREATION_MAP: dict[str, bool] = {
    "disassembly": True,
    "cleaning seat": True,
    "cleaning wood": True,
    "structural repair": True,
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

_LEGACY_OBSOLETE_SECTION_NAMES: frozenset[str] = frozenset({"sanding"})

_DEPENDENCIES: list[tuple[str, str]] = [
    ("cleaning seat", "disassembly"),
    ("cleaning wood", "disassembly"),
    ("structural repair", "disassembly"),
    ("structural repair", "cleaning wood"),
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


def get_desired_bootstrap_working_section_names() -> frozenset[str]:
    return frozenset(name for name, should_create in _SECTION_CREATION_MAP.items() if should_create)


def get_managed_bootstrap_working_section_names() -> frozenset[str]:
    return get_desired_bootstrap_working_section_names() | _LEGACY_OBSOLETE_SECTION_NAMES


def _build_expected_dependency_pairs(section_ids: dict[str, str]) -> set[tuple[str, str]]:
    return {
        (section_ids[dependent_name], section_ids[prerequisite_name])
        for dependent_name, prerequisite_name in _DEPENDENCIES
        if dependent_name in section_ids and prerequisite_name in section_ids
    }


async def _cleanup_obsolete_section(session: AsyncSession, workspace_id: str, section: WorkingSection) -> None:
    now = datetime.now(timezone.utc)

    dependency_rows = (
        await session.execute(
            select(WorkingSectionDependency).where(
                WorkingSectionDependency.workspace_id == workspace_id,
                or_(
                    WorkingSectionDependency.dependent_section_id == section.client_id,
                    WorkingSectionDependency.prerequisite_section_id == section.client_id,
                ),
            )
        )
    ).scalars().all()
    for dependency_row in dependency_rows:
        await session.delete(dependency_row)

    supported_issue_rows = (
        await session.execute(
            select(WorkingSectionSupportedIssueType).where(
                WorkingSectionSupportedIssueType.workspace_id == workspace_id,
                WorkingSectionSupportedIssueType.working_section_id == section.client_id,
            )
        )
    ).scalars().all()
    for supported_issue_row in supported_issue_rows:
        await session.delete(supported_issue_row)

    item_category_rows = (
        await session.execute(
            select(WorkingSectionItemCategory).where(
                WorkingSectionItemCategory.workspace_id == workspace_id,
                WorkingSectionItemCategory.working_section_id == section.client_id,
            )
        )
    ).scalars().all()
    for item_category_row in item_category_rows:
        await session.delete(item_category_row)

    active_memberships = (
        await session.execute(
            select(WorkingSectionMembership).where(
                WorkingSectionMembership.workspace_id == workspace_id,
                WorkingSectionMembership.working_section_id == section.client_id,
                WorkingSectionMembership.removed_at.is_(None),
            )
        )
    ).scalars().all()
    for membership in active_memberships:
        membership.removed_at = now
        membership.removed_by_id = None

    if not section.is_deleted:
        section.is_deleted = True
        section.deleted_at = now
        section.deleted_by_id = None

    await session.flush()


async def seed_working_sections(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    desired_section_names = get_desired_bootstrap_working_section_names()
    managed_section_names = get_managed_bootstrap_working_section_names()

    managed_sections = (
        await session.execute(
            select(WorkingSection).where(
                WorkingSection.workspace_id == workspace_id,
                WorkingSection.name.in_(managed_section_names),
            )
        )
    ).scalars().all()
    active_sections_by_name = {
        section.name: section
        for section in managed_sections
        if not section.is_deleted
    }
    deleted_sections_by_name = {
        section.name: section
        for section in managed_sections
        if section.is_deleted and section.name not in active_sections_by_name
    }

    section_ids: dict[str, str] = {}
    for name in desired_section_names:
        existing = active_sections_by_name.get(name) or deleted_sections_by_name.get(name)
        if existing is not None:
            existing.image = _SECTION_IMAGE_URLS.get(name)
            existing.order_list = _SECTION_ORDER_LISTS.get(name)
            existing.allows_batch_working = _SECTION_BATCH_MAP.get(name, False)
            existing.is_deleted = False
            existing.deleted_at = None
            existing.deleted_by_id = None
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

    obsolete_section_names = managed_section_names - desired_section_names
    for obsolete_name in obsolete_section_names:
        obsolete_section = active_sections_by_name.get(obsolete_name) or deleted_sections_by_name.get(obsolete_name)
        if obsolete_section is None:
            continue
        await _cleanup_obsolete_section(session, workspace_id, obsolete_section)

    expected_dependency_pairs = _build_expected_dependency_pairs(section_ids)
    existing_dependency_rows = (
        await session.execute(
            select(WorkingSectionDependency).where(
                WorkingSectionDependency.workspace_id == workspace_id,
                WorkingSectionDependency.dependent_section_id.in_(section_ids.values()),
                WorkingSectionDependency.prerequisite_section_id.in_(section_ids.values()),
            )
        )
    ).scalars().all()
    existing_dependency_pairs = {
        (row.dependent_section_id, row.prerequisite_section_id)
        for row in existing_dependency_rows
    }

    for dependency_row in existing_dependency_rows:
        dependency_pair = (dependency_row.dependent_section_id, dependency_row.prerequisite_section_id)
        if dependency_pair not in expected_dependency_pairs:
            await session.delete(dependency_row)

    for dependent_section_id, prerequisite_section_id in expected_dependency_pairs - existing_dependency_pairs:
        session.add(
            WorkingSectionDependency(
                workspace_id=workspace_id,
                dependent_section_id=dependent_section_id,
                prerequisite_section_id=prerequisite_section_id,
            )
        )
        await session.flush()

    return section_ids
