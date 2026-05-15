from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.base.identity import IdentityMixin


async def resolve_by_client_id(
    session: AsyncSession,
    model: type[IdentityMixin],
    client_id: str,
    *,
    workspace_id: str | None = None,
    include_deleted: bool = False,
) -> IdentityMixin:
    """Resolve a public client_id to an ORM instance.

    Raises NotFound if the entity does not exist, belongs to a different
    workspace, or has been soft-deleted (unless include_deleted=True).
    """
    stmt = select(model).where(model.client_id == client_id)  # type: ignore[attr-defined]

    if workspace_id is not None and hasattr(model, "workspace_id"):
        stmt = stmt.where(model.workspace_id == workspace_id)  # type: ignore[attr-defined]

    if not include_deleted and hasattr(model, "is_deleted"):
        stmt = stmt.where(model.is_deleted.is_(False))  # type: ignore[attr-defined]

    result = await session.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise NotFound(f"{model.__name__} '{client_id}' not found.")

    return instance


async def resolve_user_client_id(session: AsyncSession, user_client_id: str) -> str:
    """Validate and return a user client_id from a JWT claim or task payload."""
    from beyo_manager.models.tables.users.user import User

    stmt = select(User.client_id).where(User.client_id == user_client_id)
    result = await session.execute(stmt)
    resolved_user_id = result.scalar_one_or_none()

    if resolved_user_id is None:
        raise NotFound(f"User '{user_client_id}' not found.")

    return resolved_user_id
