from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import pytest

from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.services.infra.email_providers.base import BatchSendResult, SendResult
from beyo_manager.services.tasks.emails.handle_send_email_messages import (
    handle_send_email_messages,
)


class _ScalarList:
    def __init__(self, values: list[Any]):
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _Result:
    def __init__(self, value: Any):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self) -> _ScalarList:
        if self._value is None:
            return _ScalarList([])
        if isinstance(self._value, list):
            return _ScalarList(self._value)
        return _ScalarList([self._value])


class _Begin:
    def __init__(self, events: list[str] | None = None):
        self._events = events

    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        if self._events is not None:
            self._events.append("commit")
        return False


class _Session:
    def __init__(self, execute_results: list[Any], *, events: list[str] | None = None):
        self.execute_results = list(execute_results)
        self._events = events

    async def execute(self, _query):
        return _Result(self.execute_results.pop(0))

    def begin(self):
        return _Begin(self._events)


class _Provider:
    def __init__(self, results: list[SendResult]):
        self.results = results
        self.messages = None

    async def send_email_batch(self, messages):
        self.messages = messages
        return BatchSendResult(results=self.results)


def _connection() -> EmailConnection:
    connection = EmailConnection(
        workspace_id="ws_1",
        owner_user_id="usr_owner",
        email_address="sender@example.com",
        display_name="Sender",
        provider_type="smtp_imap",
        status="active",
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


def _message(message_id: str, *, attempted: bool = False) -> EmailMessage:
    message = EmailMessage(
        workspace_id="ws_1",
        connection_id="ecn_1",
        thread_id="eth_1",
        direction="outbound",
        from_address="sender@example.com",
        from_name="Sender",
        to_addresses_json=["to@example.com"],
        cc_addresses_json=[],
        bcc_addresses_json=[],
        subject=f"Subject {message_id}",
        text_body="Body",
        html_body=None,
        body_preview="Body",
        rfc_message_id=f"<{message_id}@example.com>",
        in_reply_to=None,
        references_json=[],
        created_by_user_id="usr_owner",
    )
    message.client_id = message_id
    message.created_at = datetime(2026, 7, 6, tzinfo=timezone.utc)
    if attempted:
        message.send_attempted_at = datetime(2026, 7, 6, 1, tzinfo=timezone.utc)
    return message


async def _session_stream(*sessions: _Session) -> AsyncIterator[_Session]:
    for session in sessions:
        yield session


def _session_factory(*sessions: _Session):
    pending_sessions = list(sessions)

    def _factory():
        async def _generator() -> AsyncIterator[_Session]:
            if pending_sessions:
                yield pending_sessions.pop(0)

        return _generator()

    return _factory


@pytest.mark.asyncio
async def test_worker_marks_attempts_and_failures(monkeypatch) -> None:
    provider = _Provider([SendResult(success=True), SendResult(success=False, error="Mailbox unavailable")])
    write_audit_calls: list[dict] = []
    dispatch_calls: list[list[Any]] = []
    lifecycle_events: list[str] = []
    pending_messages = [_message("emsg_1"), _message("emsg_2")]
    persisted_messages = [_message("emsg_1"), _message("emsg_2")]

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.get_email_provider",
        lambda _connection: provider,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.get_db_session",
        _session_factory(
            _Session([_connection(), pending_messages]),
            _Session([persisted_messages], events=lifecycle_events),
        ),
    )

    async def _write_audit(**kwargs):
        lifecycle_events.append("audit")
        write_audit_calls.append(kwargs)

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.write_audit",
        _write_audit,
    )

    async def _dispatch(events):
        lifecycle_events.append("dispatch")
        dispatch_calls.append(events)

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.event_bus.dispatch",
        _dispatch,
    )

    await handle_send_email_messages(
        {
            "workspace_id": "ws_1",
            "connection_client_id": "ecn_1",
            "message_ids": ["emsg_1", "emsg_2"],
            "request_kind": "batch_send",
            "requested_by_user_id": "usr_owner",
        },
        "task_1",
    )

    assert provider.messages is not None
    assert len(provider.messages) == 2
    assert persisted_messages[0].send_attempted_at is not None
    assert persisted_messages[0].send_error is None
    assert persisted_messages[1].send_attempted_at is not None
    assert persisted_messages[1].send_error == "Mailbox unavailable"
    assert write_audit_calls[0]["event"] == "email.delivery_completed"
    assert write_audit_calls[0]["detail"]["failed_count"] == 1
    assert lifecycle_events == ["audit", "commit", "dispatch"]
    assert len(dispatch_calls) == 1
    event = dispatch_calls[0][0]
    assert event.user_id == "usr_owner"
    assert event.event_name == "email_batch:delivery_completed"
    assert event.client_id == "task_1"
    assert event.extra == {
        "request_kind": "batch_send",
        "connection_client_id": "ecn_1",
        "attempted_count": 2,
        "sent_count": 1,
        "failed_count": 1,
        "message_ids": ["emsg_1", "emsg_2"],
    }


@pytest.mark.asyncio
async def test_worker_skips_already_attempted_messages(monkeypatch) -> None:
    provider = _Provider([])
    write_audit_calls: list[dict] = []
    dispatch_calls: list[list[Any]] = []

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.get_email_provider",
        lambda _connection: provider,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.get_db_session",
        _session_factory(_Session([_connection(), []])),
    )

    async def _write_audit(**kwargs):
        write_audit_calls.append(kwargs)

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.write_audit",
        _write_audit,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.event_bus.dispatch",
        lambda events: dispatch_calls.append(events),
    )

    await handle_send_email_messages(
        {
            "workspace_id": "ws_1",
            "connection_client_id": "ecn_1",
            "message_ids": ["emsg_1"],
            "request_kind": "send",
            "requested_by_user_id": "usr_owner",
        },
        "task_2",
    )

    assert provider.messages is None
    assert write_audit_calls == []
    assert dispatch_calls == []


@pytest.mark.asyncio
async def test_worker_skips_delivery_completed_event_without_requesting_user(monkeypatch) -> None:
    provider = _Provider([SendResult(success=True)])
    write_audit_calls: list[dict] = []
    dispatch_calls: list[list[Any]] = []
    pending_messages = [_message("emsg_1")]
    persisted_messages = [_message("emsg_1")]

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.get_email_provider",
        lambda _connection: provider,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.get_db_session",
        _session_factory(
            _Session([_connection(), pending_messages]),
            _Session([persisted_messages]),
        ),
    )

    async def _write_audit(**kwargs):
        write_audit_calls.append(kwargs)

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.write_audit",
        _write_audit,
    )

    async def _dispatch(events):
        dispatch_calls.append(events)

    monkeypatch.setattr(
        "beyo_manager.services.tasks.emails.handle_send_email_messages.event_bus.dispatch",
        _dispatch,
    )

    await handle_send_email_messages(
        {
            "workspace_id": "ws_1",
            "connection_client_id": "ecn_1",
            "message_ids": ["emsg_1"],
            "request_kind": "batch_send",
            "requested_by_user_id": None,
        },
        "task_3",
    )

    assert provider.messages is not None
    assert persisted_messages[0].send_attempted_at is not None
    assert write_audit_calls[0]["detail"]["sent_count"] == 1
    assert dispatch_calls == []
