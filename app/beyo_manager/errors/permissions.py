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
    http_status = 401

    def __init__(self, message: str, reason: str) -> None:
        self.reason = reason
        super().__init__(message, code="auth_refresh_rejected")


class PricingApiAuthError(DomainError):
    """Any refusal of the pricing app's API key. Always the same body — the cause
    is logged by `verify_pricing_api_request`, never returned."""

    http_status = 401

    def __init__(self, message: str = "Unauthorized.") -> None:
        super().__init__(message)
