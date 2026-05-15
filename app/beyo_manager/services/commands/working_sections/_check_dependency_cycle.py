from collections import deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency


async def check_for_dependency_cycle(
    session: AsyncSession,
    workspace_id: str,
    section_id: str,
    new_prerequisite_ids: list[str],
) -> None:
    """BFS over the dependency graph. Raises ConflictError if section_id would become reachable."""
    visited: set[str] = set()
    queue: deque[str] = deque(new_prerequisite_ids)

    while queue:
        current_id = queue.popleft()
        if current_id == section_id:
            raise ConflictError("Adding these dependencies would create a circular dependency.")
        if current_id in visited:
            continue
        visited.add(current_id)

        result = await session.execute(
            select(WorkingSectionDependency.prerequisite_section_id).where(
                WorkingSectionDependency.workspace_id == workspace_id,
                WorkingSectionDependency.dependent_section_id == current_id,
            )
        )
        for prerequisite_id in result.scalars().all():
            if prerequisite_id not in visited:
                queue.append(prerequisite_id)
