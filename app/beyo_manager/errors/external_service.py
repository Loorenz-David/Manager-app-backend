from beyo_manager.errors.base import DomainError


class ExternalServiceError(DomainError):
    http_status = 502

    def __init__(self, message: str = "External service request failed.") -> None:
        super().__init__(message)
