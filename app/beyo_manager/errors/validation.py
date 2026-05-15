from beyo_manager.errors.base import DomainError


class ValidationError(DomainError):
    http_status = 422

    def __init__(self, message: str = "Validation failed.") -> None:
        super().__init__(message)


class ConflictError(DomainError):
    http_status = 409

    def __init__(self, message: str = "A conflict occurred.") -> None:
        super().__init__(message)
