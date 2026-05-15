from beyo_manager.errors.base import DomainError


class NotFound(DomainError):
    http_status = 404

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(message)
