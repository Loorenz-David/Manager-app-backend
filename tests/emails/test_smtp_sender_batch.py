from __future__ import annotations

import smtplib

import pytest

from beyo_manager.services.infra.email_providers.base import OutboundMessage
from beyo_manager.services.infra.email_providers.smtp_imap import smtp_sender as smtp_sender_module
from beyo_manager.services.infra.email_providers.smtp_imap.smtp_sender import SmtpSender


def _message(index: int) -> OutboundMessage:
    return OutboundMessage(
        from_address="sender@example.com",
        from_name="Sender",
        to_addresses=[f"user{index}@example.com"],
        cc_addresses=[],
        bcc_addresses=[],
        subject=f"Subject {index}",
        text_body="Hello",
        html_body=None,
        rfc_message_id=f"<msg-{index}@example.com>",
        in_reply_to=None,
        references=[],
    )


class _FakeSMTP:
    def __init__(self, fail_map: dict[str, Exception] | None = None):
        self.fail_map = fail_map or {}
        self.logged_in = False
        self.quit_called = False
        self.sent_to: list[str] = []

    def login(self, _username: str, _password: str) -> None:
        self.logged_in = True

    def sendmail(self, _from_address: str, recipients: list[str], _message: str) -> None:
        recipient = recipients[0]
        if recipient in self.fail_map:
            raise self.fail_map[recipient]
        self.sent_to.append(recipient)

    def quit(self) -> None:
        self.quit_called = True


def test_send_batch_reuses_one_connection_per_window(monkeypatch) -> None:
    sender = SmtpSender("smtp.example.com", 587, "starttls", "user", "pass")
    messages = [_message(index) for index in range(55)]
    smtp_sessions: list[_FakeSMTP] = []

    monkeypatch.setattr(smtp_sender_module, "SMTP_BATCH_WINDOW_SIZE", 50)

    def _connect():
        smtp = _FakeSMTP()
        smtp_sessions.append(smtp)
        return smtp

    monkeypatch.setattr(sender, "_connect", _connect)

    results = sender.send_batch(messages)

    assert len(results) == 55
    assert all(result.success for result in results)
    assert len(smtp_sessions) == 2
    assert len(smtp_sessions[0].sent_to) == 50
    assert len(smtp_sessions[1].sent_to) == 5
    assert all(smtp.logged_in for smtp in smtp_sessions)
    assert all(smtp.quit_called for smtp in smtp_sessions)


def test_send_batch_marks_only_refused_recipient_as_failed(monkeypatch) -> None:
    sender = SmtpSender("smtp.example.com", 587, "starttls", "user", "pass")
    messages = [_message(index) for index in range(3)]
    smtp = _FakeSMTP(
        fail_map={
            "user1@example.com": smtplib.SMTPRecipientsRefused({"user1@example.com": (550, b"nope")})
        }
    )

    monkeypatch.setattr(sender, "_connect", lambda: smtp)

    results = sender.send_batch(messages)

    assert [result.success for result in results] == [True, False, True]
    assert "user1@example.com" in results[1].error


def test_send_batch_marks_remaining_messages_failed_after_connection_error(monkeypatch) -> None:
    sender = SmtpSender("smtp.example.com", 587, "starttls", "user", "pass")
    messages = [_message(index) for index in range(4)]

    class _BrokenSMTP(_FakeSMTP):
        def sendmail(self, _from_address: str, recipients: list[str], _message: str) -> None:
            recipient = recipients[0]
            if recipient == "user1@example.com":
                raise RuntimeError("socket closed")
            self.sent_to.append(recipient)

    monkeypatch.setattr(sender, "_connect", lambda: _BrokenSMTP())

    results = sender.send_batch(messages)

    assert [result.success for result in results] == [True, False, False, False]
    assert results[1].error == "socket closed"
