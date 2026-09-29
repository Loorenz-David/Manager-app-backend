"""The environment boundary for bootstrap, wipe-db and reset.

These routes seed accounts, truncate every table, or delete a workspace. They used to
be protected only by a shared secret, so a production server that happened to hold
the secret exposed them. They are now development tools:

- `ENVIRONMENT=production` refuses them, whatever the flag or secret says.
- Anything else must be an explicitly set, recognised non-production value AND have
  `DESTRUCTIVE_ENDPOINTS_ENABLED=true`, and the route still checks its own secret.

`ENVIRONMENT` defaults to `development` in `Settings`, so a missing value would look
like a development server. The check therefore reads whether the variable was actually
set (`model_fields_set`) and fails closed when it was not.
"""

from __future__ import annotations

import hmac

from fastapi import HTTPException

from beyo_manager.config import settings

NON_PRODUCTION_ENVIRONMENTS = frozenset(
    {"development", "testing", "validation", "staging"}
)


def _explicit_environment() -> str | None:
    if "environment" not in settings.model_fields_set:
        return None
    return (settings.environment or "").strip().lower() or None


def require_destructive_operations_allowed() -> None:
    """Raise 403 unless this server may run bootstrap, wipe-db or reset.

    Call it first in the route, before the secret check and before any session opens.
    """
    environment = _explicit_environment()
    if environment == "production":
        raise HTTPException(
            status_code=403, detail="This operation is not available in production."
        )
    if environment not in NON_PRODUCTION_ENVIRONMENTS:
        raise HTTPException(
            status_code=403,
            detail="This operation is disabled: ENVIRONMENT must be explicitly set to a non-production value.",
        )
    if not settings.destructive_endpoints_enabled:
        raise HTTPException(
            status_code=403,
            detail="This operation is disabled. Set DESTRUCTIVE_ENDPOINTS_ENABLED=true to enable it outside production.",
        )


def secret_matches(provided: str | None, expected: str | None) -> bool:
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())
