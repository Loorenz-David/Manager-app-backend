class DomainError(Exception):
    """Only DomainError subclasses cross layer boundaries."""
    http_status: int = 500

    def __init__(self, message: str = "An unexpected error occurred.") -> None:
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message
