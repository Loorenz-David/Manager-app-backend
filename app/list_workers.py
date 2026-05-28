import asyncio
import os
from sqlalchemy import select
from beyo_manager.models.database import init_db, get_db_session
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership

async def run():
    await init_db()
    async for session in get_db_session():
        query = (
            select(User.email, User.username, WorkspaceMembership.is_active, WorkspaceMembership.workspace_id)
            .join(WorkspaceMembership, User.client_id == WorkspaceMembership.user_id)
            .where(User.email.like('%@workers.beyo.dev'))
            .where(WorkspaceMembership.is_active == True)
        )
        result = await session.execute(query)
        rows = result.all()
        
        print(f"{'Email':<30} | {'Username':<20} | {'Active?':<7} | {'Workspace ID'}")
        print("-" * 80)
        for email, username, is_active, workspace_id in rows:
            print(f"{email:<32} | {username or 'N/A':<18} | {str(is_active):<7} | {workspace_id}")

if __name__ == "__main__":
    os.environ.setdefault("APP_ENV", "development")
    asyncio.run(run())
