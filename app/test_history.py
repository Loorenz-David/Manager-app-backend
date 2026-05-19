import asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, delete
from beyo_manager.services.commands.history.create_history_record import create_history_record
from beyo_manager.services.queries.history.list_history_records import list_history_records
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 1. Find admin user and capture client_id
    async with async_session() as session:
        result = await session.execute(text("SELECT client_id FROM users WHERE email = 'admin@beyo.dev'"))
        admin_client_id = result.scalar()
        if not admin_client_id:
            print("Admin user not found")
            return
        print(f"Admin client_id: {admin_client_id}")

    # 2. Create history record
    async with async_session() as session:
        record_id = await create_history_record(
            session=session,
            client_id=admin_client_id,
            entity_type='task',
            entity_client_id='task_history_smoketest_20260519',
            change_type='updated',
            field_name='state',
            from_value={'value':'open'},
            to_value={'value':'completed'},
            description='history smoke test',
            user_client_id=admin_client_id
        )
        await session.commit()
        print(f"Created record id: {record_id}")

    # 3. Fresh session call list_history_records
    async with async_session() as session:
        records, total = await list_history_records(
            session=session,
            client_id=admin_client_id,
            entity_type='task',
            entity_client_id='task_history_smoketest_20260519'
        )
        print(f"Service-query result count: {len(records)}")
        presence_in_query = any(r.client_id == record_id for r in records)
        print(f"Record present in query: {presence_in_query}")

    # 4. HTTP call
    async with httpx.AsyncClient() as client:
        # Sign in
        login_res = await client.post("http://localhost:8000/api/v1/auth/sign-in", json={
            "email":"admin@beyo.dev",
            "password":"Admin1234!",
            "app_scope":"admin"
        })
        login_data = login_res.json()
        if 'access_token' not in login_data:
            print(f"Login failed: {login_data}")
            return
        token = login_data['access_token']
        
        # Get history
        headers = {"Authorization": f"Bearer {token}"}
        history_res = await client.get(
            "http://localhost:8000/api/v1/history?entity_type=task&entity_client_id=task_history_smoketest_20260519",
            headers=headers
        )
        print(f"HTTP status: {history_res.status_code}")
        history_data = history_res.json()
        
        # The response is usually { "items": [...], "total": ... }
        items = history_data.get('items', []) if isinstance(history_data, dict) else history_data
        route_presence = any(item['client_id'] == record_id for item in items)
        print(f"Route presence: {'yes' if route_presence else 'no'}")

    # 5. Cleanup
    async with async_session() as session:
        await session.execute(delete(HistoryRecordLink).where(HistoryRecordLink.entity_client_id == 'task_history_smoketest_20260519'))
        await session.execute(delete(HistoryRecord).where(HistoryRecord.client_id == record_id))
        await session.commit()
        print("Cleanup: yes")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())
