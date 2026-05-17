#!/usr/bin/env python3
"""
TEST: User Online Status Flow
Purpose: Validate Socket.IO connect/disconnect updates user_online Redis-backed status
Run from: <project>/backend/
Usage: python tests/users/test_user_online_status.py <email> <password>
Example: python tests/users/test_user_online_status.py user_test@test.local Test1234!
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests
import socketio


BASE_URL = "http://localhost:8000"


def _fail(message: str, payload: Any | None = None) -> None:
    print(f"❌ {message}")
    if payload is not None:
        print(payload)
    raise SystemExit(1)


def sign_in(email: str, password: str) -> str:
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/sign-in",
        json={"email": email, "password": password, "app_scope": "admin"},
        timeout=10,
    )
    if resp.status_code != 200:
        _fail(f"Sign-in failed (HTTP {resp.status_code})", resp.text)

    token = resp.json().get("data", {}).get("access_token")
    if not token:
        _fail("Missing access token in sign-in response", resp.text)
    return token


def get_self_user_id(token: str) -> str:
    resp = requests.get(
        f"{BASE_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        _fail(f"GET /users/me failed (HTTP {resp.status_code})", resp.text)
    user_id = resp.json().get("data", {}).get("user", {}).get("client_id")
    if not user_id:
        _fail("Missing self user client_id", resp.text)
    return user_id


def get_live_presence(token: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/v1/users/live",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        _fail(f"GET /users/live failed (HTTP {resp.status_code})", resp.text)
    body = resp.json()
    data = body.get("data", {})
    if "presence" not in data or not isinstance(data["presence"], list):
        _fail("Invalid /users/live shape", body)
    return body


def find_user_presence(live_body: dict, user_id: str) -> dict | None:
    for item in live_body.get("data", {}).get("presence", []):
        if item.get("client_id") == user_id:
            return item
    return None


def wait_until_online_status(token: str, user_id: str, expected: bool, timeout_sec: int = 8) -> dict:
    deadline = time.time() + timeout_sec
    last_seen: dict | None = None
    while time.time() < deadline:
        body = get_live_presence(token)
        entry = find_user_presence(body, user_id)
        if entry is None:
            _fail("Self user missing in /users/live", body)
        last_seen = entry
        if bool(entry.get("is_online")) is expected:
            return entry
        time.sleep(0.5)

    _fail(
        f"Timed out waiting for is_online={expected}",
        {"last_seen": last_seen, "user_id": user_id},
    )


def open_socket_client(token: str) -> socketio.Client:
    client = socketio.Client(logger=False, engineio_logger=False)
    client.connect(BASE_URL, auth={"token": token})
    if not client.connected:
        _fail("Socket client did not connect")
    return client


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python tests/users/test_user_online_status.py <email> <password>")
        print("Example: python tests/users/test_user_online_status.py user_test@test.local Test1234!")
        raise SystemExit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    print("════════════════════════════════════════════════════════════════")
    print("TEST: User Online Status Flow")
    print("════════════════════════════════════════════════════════════════")

    print("Step 1: Authenticate")
    token = sign_in(email, password)
    user_id = get_self_user_id(token)
    print(f"✅ Authenticated as {user_id}")

    print("Step 1.5: Precondition -> user must start offline")
    # Allow prior stale sessions to expire before beginning assertions.
    baseline = wait_until_online_status(token, user_id, expected=False, timeout_sec=75)
    print("✅ User starts offline")

    print("Step 2: Connect first socket -> expect online")
    c1 = open_socket_client(token)
    wait_until_online_status(token, user_id, expected=True)
    print("✅ User is online after first connection")

    print("Step 3: Connect second socket, disconnect first -> still online")
    c2 = open_socket_client(token)
    c1.disconnect()
    wait_until_online_status(token, user_id, expected=True)
    print("✅ User remains online with second connection active")

    print("Step 4: Disconnect second socket -> expect offline")
    c2.disconnect()
    # Disconnect may be observed only after heartbeat timeout depending on transport.
    wait_until_online_status(token, user_id, expected=False, timeout_sec=75)
    print("✅ User is offline after last connection disconnects")

    print("════════════════════════════════════════════════════════════════")
    print("✅ USER ONLINE STATUS TESTS PASSED")
    print("════════════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
