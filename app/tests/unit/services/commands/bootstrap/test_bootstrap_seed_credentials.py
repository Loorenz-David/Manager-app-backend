"""Seed credentials come from configuration, never from source.

The worker seed password and the seeded mailbox used to be string literals in the
bootstrap phases. They now come from BOOTSTRAP_WORKER_PASSWORD, BOOTSTRAP_EMAIL_ADDRESS
and BOOTSTRAP_EMAIL_APP_PASSWORD. What must still hold:

- a configured worker password is what new seeded accounts can log in with;
- an existing account is never re-hashed when bootstrap runs again;
- bootstrap refuses clearly, before any database work, when the worker password is unset;
- the email seed is skipped cleanly unless both mailbox settings are present.

The session is a recorder; nothing here touches a database. Every value is a fixture.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import bcrypt
import pytest
from cryptography.fernet import Fernet

from beyo_manager.config import Settings, settings
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.bootstrap import (
    bootstrap_app as bootstrap_app_module,
)
from beyo_manager.services.commands.bootstrap.phases.seed_email_connection import (
    seed_email_connection,
)
from beyo_manager.services.commands.bootstrap.phases.seed_workers import seed_workers
from beyo_manager.services.infra.crypto.field_encryption import decrypt_field

pytestmark = pytest.mark.unit

_WORKER_PASSWORD = "fixture-worker-password"
_EMAIL_ADDRESS = "fixture.mailbox@example.test"
_EMAIL_APP_PASSWORD = "fixture-app-password"

_PHASES_DIR = Path(bootstrap_app_module.__file__).parent / "phases"


class _RoleIds(dict):
    """Any role key resolves, so the worker seed can pick whichever role it wants."""

    def get(self, key, default=None):
        return super().get(key, f"role_{key}")


class _RecordingSession:
    def __init__(self, existing_users: dict[str, User] | None = None):
        self.added: list[object] = []
        self._existing_users = existing_users or {}

    async def scalar(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is User:
            compiled = statement.compile(compile_kwargs={"literal_binds": True})
            for email, user in self._existing_users.items():
                if f"'{email}'" in str(compiled):
                    return user
        return None

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "client_id", None) is None:
            obj.client_id = f"id_{len(self.added)}"

    async def flush(self):
        return None


def _settings(**overrides) -> SimpleNamespace:
    values = {
        "bootstrap_worker_password": _WORKER_PASSWORD,
        "bootstrap_email_address": None,
        "bootstrap_email_app_password": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _workspace_result() -> _RoleIds:
    return _RoleIds(workspace_id="ws_fixture")


async def test_new_seeded_workers_get_the_configured_password():
    session = _RecordingSession()

    worker_ids = await seed_workers(
        session, _settings(), _workspace_result(), {}, "admin_fixture"
    )

    users = [obj for obj in session.added if isinstance(obj, User)]
    assert users, "no worker accounts were created"
    assert len(users) == len(worker_ids)
    for user in users:
        assert bcrypt.checkpw(_WORKER_PASSWORD.encode(), user.password.encode())
        assert not bcrypt.checkpw(b"some-other-password", user.password.encode())


async def test_existing_worker_is_not_rehashed():
    probe_session = _RecordingSession()
    await seed_workers(
        probe_session, _settings(), _workspace_result(), {}, "admin_fixture"
    )
    first_email = next(
        obj.email for obj in probe_session.added if isinstance(obj, User)
    )

    original_hash = bcrypt.hashpw(b"password-the-user-chose", bcrypt.gensalt()).decode()
    existing = User(email=first_email, username="existing", password=original_hash)
    existing.client_id = "user_existing"
    session = _RecordingSession(existing_users={first_email: existing})

    await seed_workers(
        session,
        _settings(bootstrap_worker_password="a-different-seed-password"),
        _workspace_result(),
        {},
        "admin_fixture",
    )

    assert existing.password == original_hash
    created_emails = {obj.email for obj in session.added if isinstance(obj, User)}
    assert first_email not in created_emails


@pytest.mark.parametrize("password", [None, ""])
async def test_worker_seed_refuses_to_create_accounts_without_a_password(password):
    session = _RecordingSession()

    with pytest.raises(ValidationError, match="BOOTSTRAP_WORKER_PASSWORD"):
        await seed_workers(
            session,
            _settings(bootstrap_worker_password=password),
            _workspace_result(),
            {},
            "admin_fixture",
        )

    assert not [obj for obj in session.added if isinstance(obj, User)]


@pytest.mark.parametrize("password", [None, ""])
async def test_bootstrap_refuses_before_any_database_work_without_worker_password(
    monkeypatch, password
):
    monkeypatch.setattr(settings, "bootstrap_admin_email", "admin@example.test")
    monkeypatch.setattr(settings, "bootstrap_admin_username", "fixture-admin")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "fixture-admin-password")
    monkeypatch.setattr(settings, "bootstrap_worker_password", password)

    class _UntouchableSession:
        def __getattr__(self, name):
            raise AssertionError(
                f"bootstrap touched the session ({name}) before validating its configuration"
            )

    ctx = SimpleNamespace(session=_UntouchableSession())

    with pytest.raises(ValidationError, match="BOOTSTRAP_WORKER_PASSWORD"):
        await bootstrap_app_module.bootstrap_app(ctx)


@pytest.mark.parametrize(
    ("address", "app_password"),
    [
        (None, None),
        (_EMAIL_ADDRESS, None),
        (_EMAIL_ADDRESS, ""),
        (None, _EMAIL_APP_PASSWORD),
        ("", _EMAIL_APP_PASSWORD),
        ("   ", _EMAIL_APP_PASSWORD),
    ],
)
async def test_email_seed_is_skipped_unless_both_settings_are_present(
    address, app_password
):
    session = _RecordingSession()
    owner_ids = {name: f"user_{name}" for name in _all_worker_names()}

    result = await seed_email_connection(
        session,
        _workspace_result(),
        owner_ids,
        _settings(
            bootstrap_email_address=address, bootstrap_email_app_password=app_password
        ),
    )

    assert result is None
    assert session.added == []


async def test_email_seed_uses_the_configured_mailbox(monkeypatch):
    monkeypatch.setattr(
        settings, "field_encryption_key", Fernet.generate_key().decode()
    )
    session = _RecordingSession()
    owner_ids = {name: f"user_{name}" for name in _all_worker_names()}

    result = await seed_email_connection(
        session,
        _workspace_result(),
        owner_ids,
        _settings(
            bootstrap_email_address=f"  {_EMAIL_ADDRESS} ",
            bootstrap_email_app_password=_EMAIL_APP_PASSWORD,
        ),
    )

    assert result is not None and result["seeded"] is True
    connection = next(obj for obj in session.added if isinstance(obj, EmailConnection))
    assert connection.email_address == _EMAIL_ADDRESS
    assert connection.smtp_username == _EMAIL_ADDRESS
    assert connection.imap_username == _EMAIL_ADDRESS
    assert decrypt_field(connection.smtp_password_encrypted) == _EMAIL_APP_PASSWORD
    assert decrypt_field(connection.imap_password_encrypted) == _EMAIL_APP_PASSWORD
    assert _EMAIL_APP_PASSWORD not in connection.smtp_password_encrypted
    assert any(isinstance(obj, EmailSyncState) for obj in session.added)


def test_settings_expose_the_seed_variables_with_safe_defaults(monkeypatch):
    for key in (
        "BOOTSTRAP_WORKER_PASSWORD",
        "BOOTSTRAP_EMAIL_ADDRESS",
        "BOOTSTRAP_EMAIL_APP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SECRET_KEY", "fixture")
    monkeypatch.setenv("JWT_SECRET_KEY", "fixture")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://fixture@127.0.0.1:1/fixture"
    )
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setenv("CONNECTEAM_WEBHOOK_ENABLED", "false")

    unset = Settings(_env_file=None)
    assert unset.bootstrap_worker_password is None
    assert unset.bootstrap_email_address is None
    assert unset.bootstrap_email_app_password is None

    monkeypatch.setenv("BOOTSTRAP_WORKER_PASSWORD", _WORKER_PASSWORD)
    monkeypatch.setenv("BOOTSTRAP_EMAIL_ADDRESS", _EMAIL_ADDRESS)
    monkeypatch.setenv("BOOTSTRAP_EMAIL_APP_PASSWORD", _EMAIL_APP_PASSWORD)
    configured = Settings(_env_file=None)
    assert configured.bootstrap_worker_password == _WORKER_PASSWORD
    assert configured.bootstrap_email_address == _EMAIL_ADDRESS
    assert configured.bootstrap_email_app_password == _EMAIL_APP_PASSWORD


def test_no_bootstrap_phase_assigns_a_password_literal():
    """Regression guard: a credential must not be pasted back into a seed module."""
    offenders = []
    for path in sorted(_PHASES_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            value = node.value
            if (
                any(
                    "PASSWORD" in name.upper() or "SECRET" in name.upper()
                    for name in names
                )
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and value.value
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


def _all_worker_names() -> list[str]:
    from beyo_manager.services.commands.bootstrap.phases import seed_workers as module

    return list(module._WORKER_NAMES)
