import pytest
from sqlalchemy import select

from beyo_manager.models.tables.audit.audit_log import AuditLog
from beyo_manager.services.infra.audit.write_audit import write_audit_from_event


@pytest.mark.integration
async def test_write_audit_from_event_inserts_row(db_session):
    await write_audit_from_event(
        session=db_session,
        event_name="auth:signed-in",
        workspace_id="ws_test",
        resource_client_id="usr_test",
        detail={"ip": "127.0.0.1"},
    )
    await db_session.flush()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.event == "auth:signed-in")
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.workspace_id == "ws_test"
    assert row.resource_client_id == "usr_test"
    assert row.detail == {"ip": "127.0.0.1"}


@pytest.mark.integration
async def test_detail_defaults_to_empty_dict(db_session):
    await write_audit_from_event(
        session=db_session,
        event_name="auth:signed-out",
        workspace_id="ws_test",
    )
    await db_session.flush()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.event == "auth:signed-out")
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.detail == {}
