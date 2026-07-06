from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum, EmailProviderTypeEnum
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.commands.emails.send_email import send_email
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


def _connection(*, owner_user_id: str = "usr_owner") -> EmailConnection:
    connection = EmailConnection(
        workspace_id="ws_1",
        owner_user_id=owner_user_id,
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
    return connection


def _ctx(session: _Session, incoming_data: dict[str, Any]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_owner", "role_name": "manager"},
        incoming_data=incoming_data,
        session=cast(AsyncSession, session),
    )


@pytest.mark.asyncio
async def test_send_email_enqueues_after_persisting_thread_and_message(monkeypatch) -> None:
    session = _Session(execute_results=[_connection()])
    create_task_calls: list[dict] = []
    audit_calls: list[dict] = []

    async def _create_instant_task(**kwargs):
        create_task_calls.append(kwargs)

        class _Task:
            client_id = "task_1"

        return _Task()

    async def _write_audit(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(
        "beyo_manager.services.commands.emails.send_email.create_instant_task",
        _create_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.emails.send_email.write_audit",
        _write_audit,
    )

    result = await send_email(
        _ctx(
            session,
            {
                "connection_client_id": "ecn_1",
                "to_addresses": ["alpha@example.com"],
                "subject": "Hello",
                "text_body": "Body",
                "topic": "Delivery coordination",
            },
        )
    )

    assert result == {
        "enqueued": True,
        "task_client_id": "task_1",
        "thread_client_id": "eth_01",
        "message_client_id": "emsg_02",
    }
    assert create_task_calls[0]["task_type"].value == "send_email_messages"
    assert create_task_calls[0]["payload"]["message_ids"] == ["emsg_02"]
    assert create_task_calls[0]["payload"]["request_kind"] == "send"
    assert audit_calls[0]["event"] == "email.send_enqueued"


@pytest.mark.asyncio
async def test_reply_send_preserves_threading_headers_and_enqueues(monkeypatch) -> None:
    thread = EmailThread(
        workspace_id="ws_1",
        connection_id="ecn_1",
        subject_normalized="hello",
    )
    thread.client_id = "eth_existing"

    latest_message = EmailMessage(
        workspace_id="ws_1",
        connection_id="ecn_1",
        thread_id="eth_existing",
        direction="inbound",
        from_address="sender@example.com",
        subject="Hello",
        rfc_message_id="<parent@example.com>",
        references_json=["<root@example.com>"],
    )
    latest_message.client_id = "emsg_parent"

    session = _Session(execute_results=[thread, latest_message, _connection()])
    create_task_calls: list[dict] = []
    audit_calls: list[dict] = []

    async def _create_instant_task(**kwargs):
        create_task_calls.append(kwargs)

        class _Task:
            client_id = "task_reply"

        return _Task()

    async def _write_audit(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(
        "beyo_manager.services.commands.emails.send_email.create_instant_task",
        _create_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.emails.send_email.write_audit",
        _write_audit,
    )

    result = await send_email(
        _ctx(
            session,
            {
                "thread_client_id": "eth_existing",
                "to_addresses": ["alpha@example.com"],
                "subject": "Re: Hello",
                "text_body": "Reply body",
            },
        )
    )

    created_message = next(item for item in session.added if isinstance(item, EmailMessage))
    assert created_message.in_reply_to == "<parent@example.com>"
    assert created_message.references_json == ["<root@example.com>", "<parent@example.com>"]
    assert result["task_client_id"] == "task_reply"
    assert create_task_calls[0]["payload"]["request_kind"] == "reply"
    assert audit_calls[0]["event"] == "email.reply_enqueued"
