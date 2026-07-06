import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from beyo_manager.domain.emails.guards import (
    assert_can_access_connection,
    assert_can_send_from_connection,
)
from beyo_manager.domain.emails.serializers import serialize_email_message
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.services.infra.crypto.field_encryption import decrypt_field, encrypt_field
from beyo_manager.services.infra.email_providers.base import OutboundMessage
from beyo_manager.services.infra.email_providers.smtp_imap import quote_stripper
from beyo_manager.services.infra.email_providers.smtp_imap.mime_builder import MimeBuilder
from beyo_manager.services.infra.email_providers.smtp_imap.mime_parser import MimeParser
from beyo_manager.services.infra.email_providers.smtp_imap.quote_stripper import strip_quoted_reply
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import normalize_subject
from beyo_manager.config import settings


def test_normalize_subject_strips_reply_prefixes() -> None:
    assert normalize_subject("Re: Re: Fwd: Hello") == "Hello"


def test_field_encryption_round_trip() -> None:
    original = settings.field_encryption_key
    settings.field_encryption_key = "5bWjAcj8ntcwF3pB1N90J3FJfL4wx0W1K3J2AevM2lM="
    try:
        assert decrypt_field(encrypt_field("hello")) == "hello"
    finally:
        settings.field_encryption_key = original


def test_mime_builder_sets_threading_headers() -> None:
    message = OutboundMessage(
        from_address="sender@example.com",
        from_name="Sender",
        to_addresses=["recipient@example.com"],
        cc_addresses=["copy@example.com"],
        bcc_addresses=[],
        subject="Subject",
        text_body="Hello world",
        html_body="<p>Hello world</p>",
        rfc_message_id="<msg@example.com>",
        in_reply_to="<parent@example.com>",
        references=["<root@example.com>", "<parent@example.com>"],
    )

    built = MimeBuilder().build(message)

    assert built["Message-ID"] == "<msg@example.com>"
    assert built["In-Reply-To"] == "<parent@example.com>"
    assert built["References"] == "<root@example.com> <parent@example.com>"


def test_mime_parser_extracts_headers_and_body() -> None:
    raw = (
        b"From: Sender <sender@example.com>\r\n"
        b"To: recipient@example.com\r\n"
        b"Cc: copy@example.com\r\n"
        b"Subject: Hello\r\n"
        b"Date: Tue, 04 Jul 2026 12:00:00 +0000\r\n"
        b"Message-ID: <child@example.com>\r\n"
        b"In-Reply-To: <parent@example.com>\r\n"
        b"References: <root@example.com> <parent@example.com>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Hello from email body"
    )

    parsed = MimeParser().parse(raw, uid=5, folder="INBOX")

    assert parsed.from_address == "sender@example.com"
    assert parsed.to_addresses == ["recipient@example.com"]
    assert parsed.cc_addresses == ["copy@example.com"]
    assert parsed.rfc_message_id == "<child@example.com>"
    assert parsed.in_reply_to == "<parent@example.com>"
    assert parsed.references == ["<root@example.com>", "<parent@example.com>"]
    assert parsed.text_body == "Hello from email body"
    assert parsed.text_body_clean == "Hello from email body"
    assert parsed.body_preview == "Hello from email body"
    assert parsed.received_at is not None
    assert parsed.received_at.tzinfo == timezone.utc


def test_strip_quoted_reply_removes_reply_history() -> None:
    text = (
        "yes yes fast\n\n"
        "On Sun, Jul 5, 2026 at 2:34 PM Sender <sender@example.com> wrote:\n"
        "> Hej igen\n"
        "> Kan du svara snabbt?\n"
    )

    assert strip_quoted_reply(text) == "yes yes fast"


def test_strip_quoted_reply_fallback_handles_line_wrapped_header() -> None:
    # Regression: Gmail wraps "On <date>, <name> <email>" and "wrote:" onto
    # separate lines when the header is long enough — the reported real-world
    # case that a single-line-anchored regex previously failed to strip.
    text = (
        "yes yes fast\n\n"
        "On Sun, Jul 5, 2026 at 2:34 PM Test Beyo Vintage "
        "<loorenz.david@gmail.com>\nwrote:\n\n"
        "> Hej Maria,\n"
        ">\n"
        "> Din order är klar för upphämtning hos oss.\n"
        ">\n"
        "> Vänligen svara på detta mejl om du har frågor.\n"
        "> Med vänliga hälsningar,\n"
        "> Beyo"
    )

    original = quote_stripper.EmailReplyParser
    quote_stripper.EmailReplyParser = None
    try:
        assert quote_stripper.strip_quoted_reply(text) == "yes yes fast"
    finally:
        quote_stripper.EmailReplyParser = original


def test_strip_quoted_reply_fallback_logs_warning_once(caplog) -> None:
    original = quote_stripper.EmailReplyParser
    quote_stripper.EmailReplyParser = None
    quote_stripper._fallback_warning_logged = False
    try:
        with caplog.at_level(logging.WARNING, logger=quote_stripper.__name__):
            quote_stripper.strip_quoted_reply("hello")
            quote_stripper.strip_quoted_reply("hello again")
        matches = [
            record for record in caplog.records
            if "email_reply_parser not installed" in record.message
        ]
        assert len(matches) == 1
    finally:
        quote_stripper.EmailReplyParser = original
        quote_stripper._fallback_warning_logged = False


def test_mime_parser_uses_clean_text_for_preview() -> None:
    raw = (
        b"From: Sender <sender@example.com>\r\n"
        b"To: recipient@example.com\r\n"
        b"Subject: Hello\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"yes yes fast\r\n"
        b"\r\n"
        b"On Sun, Jul 5, 2026 at 2:34 PM Sender <sender@example.com> wrote:\r\n"
        b"> Hej igen\r\n"
        b"> Kan du svara snabbt?\r\n"
    )

    parsed = MimeParser().parse(raw, uid=6, folder="INBOX")

    assert parsed.text_body is not None
    assert "On Sun, Jul 5, 2026" in parsed.text_body
    assert parsed.text_body_clean == "yes yes fast"
    assert parsed.body_preview == "yes yes fast"


def test_mime_parser_falls_back_to_raw_preview_when_clean_text_is_empty() -> None:
    raw = (
        b"From: Sender <sender@example.com>\r\n"
        b"To: recipient@example.com\r\n"
        b"Subject: Forwarded\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"On Sun, Jul 5, 2026 at 2:34 PM Sender <sender@example.com> wrote:\r\n"
        b"> Hej igen\r\n"
        b"> Kan du svara snabbt?\r\n"
    )

    parsed = MimeParser().parse(raw, uid=7, folder="INBOX")

    assert parsed.text_body_clean == ""
    assert parsed.body_preview is not None
    assert parsed.body_preview.startswith("On Sun, Jul 5, 2026")


def test_serialize_email_message_includes_text_body_clean() -> None:
    message = SimpleNamespace(
        client_id="emsg_1",
        workspace_id="ws_1",
        connection_id="econ_1",
        thread_id="ethr_1",
        direction="inbound",
        provider_folder="INBOX",
        provider_uid="10",
        from_address="sender@example.com",
        from_name="Sender",
        to_addresses_json=["recipient@example.com"],
        cc_addresses_json=[],
        bcc_addresses_json=[],
        subject="Subject",
        text_body="raw body",
        text_body_clean="clean body",
        html_body=None,
        body_preview="clean body",
        rfc_message_id="<msg@example.com>",
        in_reply_to="<parent@example.com>",
        references_json=["<parent@example.com>"],
        tracking_token=None,
        sent_or_received_at=None,
        created_by_user_id=None,
        send_attempted_at=None,
        send_error=None,
        created_at=datetime(2026, 7, 6, tzinfo=timezone.utc),
    )

    serialized = serialize_email_message(message)

    assert serialized["text_body"] == "raw body"
    assert serialized["text_body_clean"] == "clean body"


def test_access_guards_enforce_ownership() -> None:
    assert_can_access_connection("usr_owner", "seller", "usr_owner")

    try:
        assert_can_access_connection("usr_other", "seller", "usr_owner")
    except PermissionDenied:
        pass
    else:
        raise AssertionError("Expected PermissionDenied for non-owner seller access.")

    try:
        assert_can_send_from_connection("usr_other", "usr_owner")
    except PermissionDenied:
        pass
    else:
        raise AssertionError("Expected PermissionDenied when sending from another user's connection.")
