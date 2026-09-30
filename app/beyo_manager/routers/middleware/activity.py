from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from beyo_manager.config import settings
from beyo_manager.services.infra.activity.human_activity import (
    ACTIVITY_HEADER,
    SOURCE_HTTP,
    counts_as_human,
    record_human_activity,
)
from beyo_manager.services.infra.sleep.activity_tracker import ActivityTracker

# Set by routers.utils.jwt_dep.get_jwt_claims once a token has been validated.
IDENTITY_STATE_ATTR = "beyo_identity"


def _is_health_check(path: str) -> bool:
    return path == "/health" or path.startswith("/health/")


class ActivityMiddleware(BaseHTTPMiddleware):
    """Records human activity; keeps the legacy sleep touch when sleep mode is on.

    Human event (one per request, at most): an identity was stamped by
    ``get_jwt_claims`` (so the token validated — anonymous, invalid and revoked
    requests never stamp), the method is not OPTIONS, the status is not 401, and
    ``counts_as_human(method, X-Beyo-Activity)``. Routes that never depend on
    ``get_jwt_claims`` — health, webhooks, bootstrap, reset — are excluded by that.

    The write runs as the response's background task: Starlette awaits it after the
    last body chunk has been sent, inside this request's own task — so the client is
    not kept waiting, nothing outlives the request, and the write (throttled, bounded
    by a short timeout, never raising) cannot pile up tasks.
    """

    async def dispatch(self, request: Request, call_next):
        # Legacy in-app sleep (SLEEP_MODE_ENABLED=true): the old SleepMiddleware's
        # behaviour, unchanged — every non-health request touches the tracker. With the
        # flag false the tracker is inert (B-1), so it is not called at all.
        if settings.sleep_mode_enabled and not _is_health_check(request.url.path):
            ActivityTracker.touch()

        # Create the per-request state dict now, in the scope every inner layer shares,
        # so the dependency's stamp is visible here after call_next.
        state = request.state
        response = await call_next(request)

        identity = getattr(state, IDENTITY_STATE_ATTR, None)
        if (
            identity
            and request.method.upper() != "OPTIONS"
            and response.status_code != 401
            and counts_as_human(request.method, request.headers.get(ACTIVITY_HEADER))
        ):
            # call_next's response never carries a background of its own (the route's,
            # if any, already ran inside the inner app), so there is nothing to chain.
            response.background = BackgroundTask(
                record_human_activity,
                app_scope=identity.get("app_scope"),
                source=SOURCE_HTTP,
                user_id=identity.get("user_id"),
            )
        return response
