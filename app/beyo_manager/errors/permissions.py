from beyo_manager.errors.base import DomainError


class PermissionDenied(DomainError):
    http_status = 403

    def __init__(self, message: str = "You do not have permission to perform this action.", code: str | None = None) -> None:
        self.code = code
        super().__init__(message)


class AuthenticationRequired(DomainError):
    http_status = 401

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message)


class RefreshTokenRejected(PermissionDenied):
    def __init__(self, message: str, reason: str) -> None:
        self.reason = reason
        super().__init__(message, code="auth_refresh_rejected")
