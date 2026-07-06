#!/usr/bin/env python3
"""
TEST: Email SMTP/IMAP Live Flow
Purpose: Full end-to-end validation of the email feature against a real Gmail account.
         Covers: connection create → test → send → sync → thread/message read → mark read → unread count → delete.

Run from: <project>/backend/
Usage (self-send loopback — tests IMAP sync, inbound lands in a new thread):
    python tests/emails/test_email_live.py <app_email> <app_password> <gmail_address> <gmail_app_password>

Usage (send to external address — tests full reply-threading flow):
    python tests/emails/test_email_live.py <app_email> <app_password> <gmail_address> <gmail_app_password> --send-to <recipient_email>

    After the outbound email is sent the script pauses and prints instructions.
    Open <recipient_email>'s inbox, reply to the test email (a simple "Reply" from that mailbox),
    then press Enter in this terminal to trigger the sync and verify the reply was matched to the thread.

Arguments:
    app_email          Email address of a workspace user in the app (for JWT sign-in).
    app_password       Password for that user.
    gmail_address      The Gmail address registered as the SMTP/IMAP connection in the app.
    gmail_app_password A 16-character Google App Password for that Gmail account.
                       Generate at: Google Account → Security → 2-Step Verification → App Passwords.
                       Enter the 16 characters WITHOUT spaces.

    --send-to <email>  Optional. Send the test email to this address instead of self.
                       After sending, the script pauses so you can manually reply,
                       then verifies that the reply is matched to the original thread.

Gmail requirements before running:
    1. IMAP must be enabled: Gmail Settings → See All Settings → Forwarding and POP/IMAP → Enable IMAP.
    2. Use an App Password, NOT your main Gmail password.
    3. Use a DEDICATED TEST ACCOUNT — this test reads your INBOX.

Example:
    python tests/emails/test_email_live.py admin@company.com Admin1234! test.mailbox@gmail.com abcdabcdabcdabcd
    python tests/emails/test_email_live.py admin@company.com Admin1234! test.mailbox@gmail.com abcdabcdabcdabcd --send-to friend@example.com
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests

BASE_URL = "http://localhost:8000"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_SECURITY = "starttls"

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
IMAP_SECURITY = "ssl"

INBOX_FOLDER = "INBOX"

WORKER_POLL_INTERVAL_S = 6
WORKER_POLL_MAX_ATTEMPTS = 15  # up to ~90 seconds for Gmail delivery + worker processing


# ── helpers ───────────────────────────────────────────────────────────────────


def _pass(message: str, payload: Any | None = None) -> None:
    print(f"  ✓  {message}")
    if payload is not None:
        print(f"     {payload}")


def _warn(message: str, payload: Any | None = None) -> None:
    print(f"  ⚠  {message}")
    if payload is not None:
        print(f"     {payload}")


def _fail(message: str, payload: Any | None = None) -> None:
    print(f"\n  ✗  FAIL: {message}")
    if payload is not None:
        print(f"     {payload}")
    raise SystemExit(1)


def _section(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, 60 - len(title))}")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _assert_ok(resp: requests.Response, label: str) -> dict:
    if resp.status_code not in (200, 201):
        _fail(f"{label} — HTTP {resp.status_code}", resp.text[:800])
    body = resp.json()
    if not body.get("success", True):
        _fail(f"{label} — success=false", body)
    return body.get("data", body)


# ── step functions ─────────────────────────────────────────────────────────────


def sign_in(app_email: str, app_password: str) -> str:
    _section("Step 1 — Sign in")
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/sign-in",
        json={"email": app_email, "password": app_password, "app_scope": "admin"},
        timeout=10,
    )
    data = _assert_ok(resp, "POST /auth/sign-in")
    token = data.get("access_token")
    if not token:
        _fail("Missing access_token in sign-in response", data)
    _pass(f"Signed in as {app_email}")
    return token


def create_connection(token: str, gmail_address: str, gmail_app_password: str) -> str:
    _section("Step 2 — Create email connection")
    resp = requests.post(
        f"{BASE_URL}/api/v1/email-connections",
        headers=_headers(token),
        json={
            "email_address": gmail_address,
            "display_name": "Live Test Mailbox",
            "provider_type": "smtp_imap",
            "smtp_host": SMTP_HOST,
            "smtp_port": SMTP_PORT,
            "smtp_security": SMTP_SECURITY,
            "smtp_username": gmail_address,
            "smtp_password": gmail_app_password,
            "imap_host": IMAP_HOST,
            "imap_port": IMAP_PORT,
            "imap_security": IMAP_SECURITY,
            "imap_username": gmail_address,
            "imap_password": gmail_app_password,
            "inbox_folder": INBOX_FOLDER,
        },
        timeout=15,
    )
    data = _assert_ok(resp, "POST /email-connections")
    conn = data.get("email_connection", {})
    connection_id = conn.get("client_id")
    if not connection_id:
        _fail("Missing client_id in email_connection response", data)

    if "smtp_password" in str(data) or "imap_password" in str(data):
        _fail("SECURITY: plaintext password appeared in create_connection response", data)
    if "smtp_password_encrypted" in str(data) or "imap_password_encrypted" in str(data):
        _fail("SECURITY: encrypted password field appeared in create_connection response", data)

    _pass(f"Connection created: {connection_id}")
    _pass(f"status={conn.get('status')}  smtp={conn.get('smtp_host')}:{conn.get('smtp_port')}  imap={conn.get('imap_host')}:{conn.get('imap_port')}")
    return connection_id


def test_connection(token: str, connection_id: str) -> None:
    _section("Step 3 — Test connection (SMTP + IMAP reachability)")
    resp = requests.post(
        f"{BASE_URL}/api/v1/email-connections/{connection_id}/test",
        headers=_headers(token),
        timeout=30,
    )
    data = _assert_ok(resp, f"POST /email-connections/{connection_id}/test")

    smtp_ok = data.get("smtp_ok")
    imap_ok = data.get("imap_ok")
    reachable = data.get("reachable")

    if data.get("smtp_error"):
        _fail(f"SMTP connection failed: {data['smtp_error']}")
    if data.get("imap_error"):
        _fail(f"IMAP connection failed: {data['imap_error']}")
    if not reachable:
        _fail("Connection test returned reachable=false", data)

    _pass(f"SMTP reachable: {smtp_ok}  IMAP reachable: {imap_ok}")


def check_topic_presets(token: str) -> None:
    _section("Step 4 — Verify topic presets")
    resp = requests.get(
        f"{BASE_URL}/api/v1/email-threads/topic-presets",
        headers=_headers(token),
        timeout=10,
    )
    data = _assert_ok(resp, "GET /email-threads/topic-presets")
    presets = data.get("email_thread_topic_presets", [])

    if len(presets) < 6:
        _fail(f"Expected ≥6 seeded presets, got {len(presets)}", presets)

    labels = [p["label"] for p in presets]
    if "Delivery coordination" not in labels:
        _fail("'Delivery coordination' preset missing from preset list", labels)

    sort_orders = [p["sort_order"] for p in presets]
    if sort_orders != sorted(sort_orders):
        _fail("Presets are not ordered by sort_order ASC", sort_orders)

    _pass(f"{len(presets)} presets returned, ordered correctly")
    for p in presets:
        _pass(f"  [{p['sort_order']}] {p['label']}")


def send_email(token: str, connection_id: str, recipient: str) -> tuple[str, str, str]:
    """Send a test email to recipient. Returns (thread_id, message_id, subject)."""
    _section(f"Step 5 — Send outbound email → {recipient}")
    subject = f"[LIVE TEST] Email feature smoke test {int(time.time())}"
    resp = requests.post(
        f"{BASE_URL}/api/v1/email-threads/send",
        headers=_headers(token),
        json={
            "connection_client_id": connection_id,
            "to_addresses": [recipient],
            "subject": subject,
            "text_body": (
                "This is an automated live test email.\n"
                "If you see this in your inbox, the send flow works correctly.\n"
                "Please reply to this message to test the inbound reply-matching flow."
            ),
            "topic": "Delivery coordination",
        },
        timeout=30,
    )
    data = _assert_ok(resp, "POST /email-threads/send")

    thread_id = data.get("thread_client_id")
    message_id = data.get("message_client_id")
    enqueued = data.get("enqueued")
    task_client_id = data.get("task_client_id")

    if not thread_id:
        _fail("Missing thread_client_id in send response", data)
    if not message_id:
        _fail("Missing message_client_id in send response", data)
    if not enqueued:
        _fail("Expected enqueued=true in send response", data)
    if not task_client_id:
        _fail("Missing task_client_id in send response", data)

    _pass(f"Email queued — task={task_client_id}  thread={thread_id}  message={message_id}")
    _pass(f"Subject: {subject}")
    return thread_id, message_id, subject


def verify_thread(token: str, thread_id: str) -> None:
    _section("Step 6 — Verify thread was created with correct topic")
    resp = requests.get(
        f"{BASE_URL}/api/v1/email-threads/{thread_id}",
        headers=_headers(token),
        timeout=10,
    )
    data = _assert_ok(resp, f"GET /email-threads/{thread_id}")
    thread = data.get("email_thread", {})

    if thread.get("topic") != "Delivery coordination":
        _fail(f"Expected topic='Delivery coordination', got {thread.get('topic')!r}", thread)
    if thread.get("client_id") != thread_id:
        _fail("Thread client_id mismatch", thread)

    _pass(f"topic='{thread.get('topic')}'  subject_normalized='{thread.get('subject_normalized')}'")


def verify_outbound_message(token: str, thread_id: str, message_id: str) -> None:
    _section("Step 7 — Verify outbound message in thread")
    resp = requests.get(
        f"{BASE_URL}/api/v1/email-threads/{thread_id}/messages",
        headers=_headers(token),
        timeout=10,
    )
    data = _assert_ok(resp, f"GET /email-threads/{thread_id}/messages")
    messages = data.get("email_messages", [])

    if len(messages) == 0:
        _fail("No messages returned for thread after send", data)

    outbound = next((m for m in messages if m["client_id"] == message_id), None)
    if outbound is None:
        _fail(f"Sent message {message_id} not found in thread message list", messages)
    if outbound.get("direction") != "outbound":
        _fail(f"Expected direction=outbound, got {outbound.get('direction')!r}", outbound)
    if "raw_headers_json" in outbound:
        _fail("SECURITY: raw_headers_json appeared in message response — must be omitted", outbound)

    _pass(f"Outbound message found: direction={outbound['direction']}  rfc_message_id={outbound.get('rfc_message_id')!r}")


def wait_for_manual_reply(subject: str, recipient: str) -> None:
    """Pause and prompt the user to manually reply before continuing the sync flow."""
    _section("Step 8 — Manual reply (external sender)")
    print()
    print(f"  ┌{'─' * 62}┐")
    print("  │  ACTION REQUIRED                                             │")
    print("  │                                                              │")
    print(f"  │  Open the inbox for: {recipient:<40}│")
    print("  │                                                              │")
    print("  │  Find the email with subject:                                │")
    print(f"  │    {subject[:58]:<58}│")
    print("  │                                                              │")
    print("  │  Reply to it (a simple 'Reply' is enough).                   │")
    print("  │  Then come back here and press Enter.                        │")
    print(f"  └{'─' * 62}┘")
    print()
    try:
        input("  >> Press Enter once you have replied...")
    except EOFError:
        pass
    _pass("Manual reply confirmed. Starting sync poll...")


def trigger_sync_and_wait(
    token: str,
    connection_id: str,
    thread_id: str,
    expect_reply_in_thread: bool = True,
) -> bool:
    """
    Triggers inbox sync and polls for an inbound message.

    If expect_reply_in_thread=True, polls the original thread's messages for a
    direction=inbound message (reply-matching test).

    If expect_reply_in_thread=False (self-send loopback), polls the thread list
    for any thread with an inbound message (basic IMAP sync test).

    Returns True if inbound message found, False if timed out.
    """
    label = "Step 8" if not expect_reply_in_thread else "Step 9"
    _section(f"{label} — Trigger IMAP sync and wait for inbound message")

    resp = requests.post(
        f"{BASE_URL}/api/v1/email-connections/{connection_id}/sync",
        headers=_headers(token),
        timeout=15,
    )
    data = _assert_ok(resp, f"POST /email-connections/{connection_id}/sync")
    sync_state = data.get("sync_state", {})
    _pass(f"Sync task enqueued — folder={sync_state.get('folder')}  last_seen_uid={sync_state.get('last_seen_uid')}")

    _warn("Waiting for Gmail delivery + worker to process sync...")
    _warn(f"Polling every {WORKER_POLL_INTERVAL_S}s, up to {WORKER_POLL_MAX_ATTEMPTS} attempts (~{WORKER_POLL_INTERVAL_S * WORKER_POLL_MAX_ATTEMPTS}s total)")

    for attempt in range(1, WORKER_POLL_MAX_ATTEMPTS + 1):
        time.sleep(WORKER_POLL_INTERVAL_S)

        if expect_reply_in_thread:
            resp = requests.get(
                f"{BASE_URL}/api/v1/email-threads/{thread_id}/messages",
                headers=_headers(token),
                timeout=10,
            )
            if resp.status_code != 200:
                _warn(f"  attempt {attempt}/{WORKER_POLL_MAX_ATTEMPTS} — HTTP {resp.status_code}")
                continue

            messages = resp.json().get("data", {}).get("email_messages", [])
            inbound = [m for m in messages if m.get("direction") == "inbound"]

            if inbound:
                _pass(f"Inbound reply arrived after ~{attempt * WORKER_POLL_INTERVAL_S}s")
                _pass(f"in_reply_to={inbound[0].get('in_reply_to')!r}")
                _pass(f"Thread matched: {len(messages)} message(s) total ({len(inbound)} inbound)")
                return True
        else:
            # Loopback: look for any inbound in the connection's thread list
            resp = requests.get(
                f"{BASE_URL}/api/v1/email-threads",
                headers=_headers(token),
                params={"connection_client_id": connection_id},
                timeout=10,
            )
            if resp.status_code != 200:
                _warn(f"  attempt {attempt}/{WORKER_POLL_MAX_ATTEMPTS} — HTTP {resp.status_code}")
                continue

            threads = resp.json().get("data", {}).get("email_threads", [])
            total_threads = len(threads)
            if total_threads > 1:
                # Loopback creates a separate thread for the inbound (no In-Reply-To match)
                _pass(f"Inbound arrived after ~{attempt * WORKER_POLL_INTERVAL_S}s (loopback — new thread created)")
                _pass(f"{total_threads} thread(s) total in connection")
                return True

        if attempt == 3:
            _warn("  Re-triggering sync (Gmail delivery may be delayed)...")
            requests.post(
                f"{BASE_URL}/api/v1/email-connections/{connection_id}/sync",
                headers=_headers(token),
                timeout=15,
            )

        print(f"     attempt {attempt}/{WORKER_POLL_MAX_ATTEMPTS} — no inbound yet")

    _warn("Inbound message did not arrive within the polling window.")
    _warn("Check: worker is running, EMAIL_INBOX_SYNC tasks are being processed, Gmail IMAP is enabled.")
    return False


def mark_thread_read_and_verify(token: str, thread_id: str, step: int) -> None:
    _section(f"Step {step} — Mark thread as read")

    resp_before = requests.get(
        f"{BASE_URL}/api/v1/email-threads/{thread_id}",
        headers=_headers(token),
        timeout=10,
    )
    data_before = _assert_ok(resp_before, f"GET /email-threads/{thread_id} (before mark)")
    is_unread_before = data_before.get("email_thread", {}).get("is_unread")
    _pass(f"is_unread before mark_read: {is_unread_before}")

    resp = requests.post(
        f"{BASE_URL}/api/v1/email-threads/{thread_id}/read",
        headers=_headers(token),
        timeout=10,
    )
    data = _assert_ok(resp, f"POST /email-threads/{thread_id}/read")
    if not data.get("marked_read"):
        _fail("mark_email_thread_read returned marked_read=false", data)

    resp2 = requests.post(
        f"{BASE_URL}/api/v1/email-threads/{thread_id}/read",
        headers=_headers(token),
        timeout=10,
    )
    _assert_ok(resp2, f"POST /email-threads/{thread_id}/read (idempotency check)")
    _pass("Second mark_read call succeeded (idempotency confirmed)")

    resp_after = requests.get(
        f"{BASE_URL}/api/v1/email-threads/{thread_id}",
        headers=_headers(token),
        timeout=10,
    )
    data_after = _assert_ok(resp_after, f"GET /email-threads/{thread_id} (after mark)")
    is_unread_after = data_after.get("email_thread", {}).get("is_unread")

    if is_unread_after is not False:
        _fail(f"Expected is_unread=False after mark_read, got {is_unread_after!r}", data_after)
    _pass(f"is_unread after mark_read: {is_unread_after} ✓")


def check_unread_count(token: str, connection_id: str, expected: int, label: str) -> None:
    resp = requests.get(
        f"{BASE_URL}/api/v1/email-threads/unread-count",
        headers=_headers(token),
        params={"connection_client_id": connection_id},
        timeout=10,
    )
    data = _assert_ok(resp, f"GET /email-threads/unread-count ({label})")
    count = data.get("unread_count")
    if count != expected:
        _warn(f"unread_count={count}, expected {expected} ({label})")
    else:
        _pass(f"unread_count={count} as expected ({label})")


def list_threads(token: str, connection_id: str, step: int) -> None:
    _section(f"Step {step} — List threads for connection")
    resp = requests.get(
        f"{BASE_URL}/api/v1/email-threads",
        headers=_headers(token),
        params={"connection_client_id": connection_id},
        timeout=10,
    )
    data = _assert_ok(resp, "GET /email-threads")
    threads = data.get("email_threads", [])
    pagination = data.get("email_threads_pagination", {})

    if len(threads) == 0:
        _fail("No threads returned for connection after send", data)

    _pass(f"{len(threads)} thread(s) returned  has_more={pagination.get('has_more')}")
    for t in threads:
        _pass(f"  [{t.get('client_id')}] topic={t.get('topic')!r}  is_unread={t.get('is_unread')}  last_message_at={t.get('last_message_at')}")


def delete_connection(token: str, connection_id: str, step: int) -> None:
    _section(f"Step {step} — Delete connection (cleanup)")
    resp = requests.delete(
        f"{BASE_URL}/api/v1/email-connections/{connection_id}",
        headers=_headers(token),
        timeout=10,
    )
    data = _assert_ok(resp, f"DELETE /email-connections/{connection_id}")
    if not data.get("deleted"):
        _fail("Delete returned deleted=false", data)
    _pass(f"Connection {connection_id} deleted")


# ── main ───────────────────────────────────────────────────────────────────────


def _parse_args() -> tuple[str, str, str, str, str | None]:
    """Returns (app_email, app_password, gmail_address, gmail_app_password, send_to)."""
    args = sys.argv[1:]
    send_to: str | None = None

    if "--send-to" in args:
        idx = args.index("--send-to")
        if idx + 1 >= len(args):
            print("Error: --send-to requires a recipient email address.")
            raise SystemExit(1)
        send_to = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if len(args) != 4:
        print(__doc__)
        raise SystemExit(1)

    app_email, app_password, gmail_address, gmail_app_password = args
    gmail_app_password = gmail_app_password.replace(" ", "")
    return app_email, app_password, gmail_address, gmail_app_password, send_to


def main() -> None:
    app_email, app_password, gmail_address, gmail_app_password, send_to = _parse_args()

    manual_reply_mode = send_to is not None
    recipient = send_to or gmail_address

    print(f"\n{'═' * 64}")
    print("  EMAIL LIVE TEST")
    print(f"  App user   : {app_email}")
    print(f"  Mailbox    : {gmail_address}")
    print(f"  Send to    : {recipient}")
    print(f"  Mode       : {'manual-reply (external recipient)' if manual_reply_mode else 'loopback (self-send)'}")
    print(f"  Server     : {BASE_URL}")
    print(f"{'═' * 64}")

    connection_id: str | None = None
    inbound_arrived = False

    try:
        token = sign_in(app_email, app_password)
        connection_id = create_connection(token, gmail_address, gmail_app_password)
        test_connection(token, connection_id)
        check_topic_presets(token)
        thread_id, message_id, subject = send_email(token, connection_id, recipient)
        verify_thread(token, thread_id)
        verify_outbound_message(token, thread_id, message_id)

        if manual_reply_mode:
            wait_for_manual_reply(subject, recipient)
            _section("Step 9b — Unread count before sync")
            check_unread_count(token, connection_id, expected=0, label="before sync")
            inbound_arrived = trigger_sync_and_wait(
                token, connection_id, thread_id, expect_reply_in_thread=True
            )
            if inbound_arrived:
                _section("Step 9c — Unread count after inbound reply")
                check_unread_count(token, connection_id, expected=1, label="after inbound")
                mark_thread_read_and_verify(token, thread_id, step=10)
                _section("Step 10b — Unread count after mark read")
                check_unread_count(token, connection_id, expected=0, label="after mark_read")
            else:
                _warn("Reply did not arrive — skipping inbound-dependent steps")
                _warn("Check: worker is running and processing EMAIL_INBOX_SYNC, Gmail replied correctly")
            list_threads(token, connection_id, step=11)
            delete_connection(token, connection_id, step=12)
        else:
            _section("Step 8b — Unread count before sync")
            check_unread_count(token, connection_id, expected=0, label="before sync")
            inbound_arrived = trigger_sync_and_wait(
                token, connection_id, thread_id, expect_reply_in_thread=False
            )
            if inbound_arrived:
                _warn("Loopback: inbound arrived in a separate thread (no In-Reply-To header on fresh send)")
                _warn("This confirms IMAP sync works. Use --send-to to test reply-thread matching.")
            else:
                _warn("Inbound not detected. Check: worker running, EMAIL_INBOX_SYNC dispatched, Gmail IMAP enabled.")
            list_threads(token, connection_id, step=10)
            delete_connection(token, connection_id, step=11)

    except SystemExit:
        if connection_id and "token" in dir():
            try:
                delete_connection(token, connection_id, step=99)
            except Exception:
                _warn(f"Cleanup failed — manually delete connection {connection_id}")
        raise

    print(f"\n{'═' * 64}")
    if manual_reply_mode:
        if inbound_arrived:
            print("  ALL STEPS PASSED — full reply-thread matching test complete")
        else:
            print("  SEND/CONNECTION STEPS PASSED")
            print("  INBOUND REPLY: not detected (check worker logs)")
    else:
        print("  SEND/CONNECTION STEPS PASSED")
        if inbound_arrived:
            print("  IMAP SYNC: inbound detected (loopback — no thread matching)")
        else:
            print("  IMAP SYNC: timed out (check worker logs)")
    print(f"{'═' * 64}\n")


if __name__ == "__main__":
    main()
