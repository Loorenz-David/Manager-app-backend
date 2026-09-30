from beyo_manager.errors.base import DomainError

AUTH_UNAVAILABLE_CODE = "auth_unavailable"
AUTH_UNAVAILABLE_RETRY_AFTER_SECONDS = 5


class AuthUnavailableError(DomainError):
    """The server cannot currently *validate* credentials (e.g. the Redis-backed
    token blocklist or the sign-in rate limiter is unreachable).

    This is not a 401: the credentials may be perfectly valid, so a client must not
    discard its session. It is a 503 with ``code: "auth_unavailable"`` and a
    ``Retry-After`` header, so the client knows to retry rather than sign out.
    ``reason`` is an optional finer-grained cause carried into the body.
    """

    http_status = 503
    code = AUTH_UNAVAILABLE_CODE
    retry_after_seconds = AUTH_UNAVAILABLE_RETRY_AFTER_SECONDS

    def __init__(
        self,
        message: str = "Authentication is temporarily unavailable. Please retry.",
        reason: str | None = None,
    ) -> None:
        self.reason = reason
        super().__init__(message)
