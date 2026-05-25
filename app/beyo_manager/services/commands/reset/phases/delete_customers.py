from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.customers.customer import Customer


async def delete_customers(session: AsyncSession, workspace_id: str) -> None:
    """Delete all Customer rows for workspace."""
    await session.execute(
        delete(Customer).where(
            Customer.workspace_id == workspace_id,
        )
    )
