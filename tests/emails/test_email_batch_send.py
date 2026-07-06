from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum, EmailProviderTypeEnum
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.commands.emails.send_email_batch import send_email_batch
from beyo_manager.services.context import ServiceContext


class _ScalarResult:
    def __init__(self, value: Any):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Begin:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Session:
    def __init__(self, *, execute_results: list[Any] | None = None):
        self.execute_results = list(execute_results or [])
        self.added: list[Any] = []
        self.flush_calls = 0

    def in_transaction(self) -> bool:
        return False

    def begin(self):
        return _Begin()

    async def execute(self, _query):
        if self.execute_results:
            return _ScalarResult(self.execute_results.pop(0))
        return _ScalarResult(None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1
        for obj in self.added:
            if isinstance(obj, EmailThread) and not getattr(obj, "client_id", None):
                obj.client_id = f"eth_{self.flush_calls:02d}"
            if isinstance(obj, EmailMessage) and not getattr(obj, "client_id", None):
                obj.client_id = f"emsg_{self.flush_calls:02d}"


def _ctx(session: _Session, incoming_data: dict[str, Any]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_owner"},
        incoming_data=incoming_data,
        session=cast(AsyncSession, session),
    )


@pytest.mark.asyncio
async def test_send_email_batch_enqueues_and_persists_all_records(monkeypatch) -> None:
    connection = EmailConnection(
        workspace_id="ws_1",
        owner_user_id="usr_owner",
        email_address="sender@example.com",
        display_name="Sender",
        provider_type=EmailProviderTypeEnum.SMTP_IMAP.value,
        status=EmailConnectionStatusEnum.ACTIVE.value,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_security="starttls",
        smtp_username="sender@example.com",
        smtp_password_encrypted="encrypted",
        imap_host="imap.example.com",
        imap_port=993,
        imap_security="ssl",
        imap_username="sender@example.com",
        imap_password_encrypted="encrypted",
        inbox_folder="INBOX",
    )
    connection.client_id = "ecn_1"

    session = _Session(execute_results=[connection])
    create_task_calls: list[dict] = []
    audit_calls: list[dict] = []

    async def _write_audit(**kwargs):
        audit_calls.append(kwargs)

    async def _create_instant_task(**kwargs):
        create_task_calls.append(kwargs)

        class _Task:
            client_id = "task_1"

        return _Task()

    monkeypatch.setattr(
        "beyo_manager.services.commands.emails.send_email_batch.write_audit",
        _write_audit,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.emails.send_email_batch.create_instant_task",
        _create_instant_task,
    )

    result = await send_email_batch(
        _ctx(
            session,
            {
                "connection_client_id": "ecn_1",
                "targets": [
                    {
                        "to_addresses": ["alpha@example.com"],
                        "entity_type": "customer",
                        "entity_client_id": "cus_1",
                        "topic": "Follow-up",
                    },
                    {
                        "to_addresses": ["beta@example.com"],
                        "entity_type": "customer",
                        "entity_client_id": "cus_2",
                        "topic": "Follow-up",
                    },
                ],
                "cc_addresses": ["copy@example.com"],
                "bcc_addresses": ["blind@example.com"],
                "subject": "Hello",
                "text_body": "Batch body",
            },
        )
    )

    assert result["target_count"] == 2
    assert result["enqueued"] is True
    assert result["task_client_id"] == "task_1"
    assert result["queued_count"] == 2
    assert [item["to_addresses"] for item in result["results"]] == [
        ["alpha@example.com"],
        ["beta@example.com"],
    ]
    assert len([item for item in session.added if isinstance(item, EmailThread)]) == 2
    assert len([item for item in session.added if isinstance(item, EmailMessage)]) == 2
    assert create_task_calls[0]["task_type"].value == "send_email_messages"
    assert create_task_calls[0]["payload"]["message_ids"] == ["emsg_02", "emsg_04"]
    assert create_task_calls[0]["payload"]["request_kind"] == "batch_send"
    assert audit_calls[0]["event"] == "email.batch_send_enqueued"
    assert audit_calls[0]["detail"] == {
        "target_count": 2,
        "queued_count": 2,
        "connection_id": "ecn_1",
        "task_client_id": "task_1",
    }
