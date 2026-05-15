from beyo_manager.errors.base import DomainError


class PermissionDenied(DomainError):
    http_status = 403

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)


class AuthenticationRequired(DomainError):
    http_status = 401

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message)
